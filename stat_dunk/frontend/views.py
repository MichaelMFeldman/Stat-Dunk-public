from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.template import Context, loader, RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.http import Http404
from .forms import QuestionBuilderForm
from django.views.generic import View, FormView, TemplateView
from error import write_error

import psycopg2
import json
from StatsObject import StatsObject
from Question import Question
from MulticondQuestion import AST_rate_Q, REB_rate_Q, offensive_rtg_Q, defensive_rtg_Q

from django.core.servers.basehttp import FileWrapper
from xlrd import open_workbook
from xlutils.copy import copy
import time
import string, random
from statdunk.frontend.models import Uploaded_File

class QuestionBuilderView(FormView):
    template_name = "questionbuilder.html"
    form_class = QuestionBuilderForm
    
def GetSchools(HttpRequest):
    conn = psycopg2.connect("dbname=game_data user=sd_readonly")
    cur = conn.cursor()
    cur.execute("SELECT school_id, name FROM schools")
    data = cur.fetchall()
    cur.close()
    conn.close()
    schools = {i[0]: i[1] for i in data} # {school id: name}
    return HttpResponse(json.dumps(schools))

def GetSchoolInfo(HttpRequest, school_id):
    school_id = int(school_id)
    conn = psycopg2.connect("dbname=game_data user=sd_readonly")
    cur = conn.cursor()
    
    cur.execute("""SELECT game_id, home_school_id, away_school_id, winner,
                   home_score, away_score, date
                   FROM games WHERE %s in (home_school_id, away_school_id)
                   ORDER BY date""",
                (school_id,))
                
    # list of {"game_id": game id, "oppt_id": school id, "is_win": bool,
    #          "team_score": int, "oppt_score": int, "year/month/day": int}
    games = [{"game_id": i[0],
              "oppt_id": i[1] if school_id != i[1] else i[2],
              "is_win": True if school_id == i[3] else False,
              "team_score": i[4] if school_id == i[1] else i[5],
              "oppt_score": i[5] if school_id == i[1] else i[4],
              "year": i[6].year,
              "month": i[6].month,
              "day": i[6].day}
              for i in cur.fetchall()]
              
    cur.execute("""SELECT player_id, last_name, first_name, title
                   FROM players
                   WHERE school_id = %s AND last_name != 'TEAM'
                   ORDER BY last_name""",
                   (school_id,))
                   
    # list of {"player_id": player id, "last/first": last/first name, "title": None or title}
    players = [{"player_id": i[0],
                "last": i[1],
                "first": i[2],
                "title": i[3],
                "school_id": school_id}
                for i in cur.fetchall()]
                                
    cur.close()
    conn.close()
    return HttpResponse(json.dumps({"games": games, "players": players}))

# Everything but stats is represented by IDs of some sort, which are given as
# strings (everything is passed through JSON.stringify())
def string_list_into_int_set(the_list):
    new_set = set()
    for i in the_list:
        new_set.add(int(i))
    return new_set

def get_params(HttpRequest):
    # For some reason, all the data is the key of a dictionary (the value is '')
    for i in HttpRequest.GET.iterkeys():
        params = json.loads(i)
        break
        
    try:
        school_id = int(params["school_id"])
    except KeyError:
        write_error("The school ID was not found. " + str(HttpRequest.GET))
        return False
        
    try:
        games =              string_list_into_int_set(params["games"])
        on_court =           string_list_into_int_set(params["on_court"])
        off_court =          string_list_into_int_set(params["off_court"])
        making_actions =     string_list_into_int_set(params["making_actions"])
        not_making_actions = string_list_into_int_set(params["not_making_actions"])
        stats =              params["stats"]
    except ValueError:
        write_error("A parameter was unexpectedly not an integer. " + str(HttpRequest.GET))
        return False
    else:
        return (school_id, games, on_court, off_court,
                making_actions, not_making_actions, stats)

def Calculate(HttpRequest):
    try:
        result = get_params(HttpRequest)
        if not result:
            return HttpResponse(json.dumps(False))
        else:
            school_id, g, on_c, off_c, m_act, n_m_act, stats = result
                
        question_methods = []
        question_answers = []
        multicond_questions = []
        multicond_answers = []
        
        for stat in stats:
            if stat["type"] == "ASTrate":
                multicond_questions += [AST_rate_Q(games=g, on_court=on_c, not_on_court=off_c,
                                                   requested_players=m_act)]
                stat["answer_location"] = ("m", len(multicond_questions)-1)
            elif stat["type"] == "Orebrate":
                multicond_questions += [REB_rate_Q(games=g, on_court=on_c, not_on_court=off_c,
                                                   requested_players=m_act,
                                                   rebound_type="OREB")]
                stat["answer_location"] = ("m", len(multicond_questions)-1)
            elif stat["type"] == "Drebrate":
                multicond_questions += [REB_rate_Q(games=g, on_court=on_c, not_on_court=off_c,
                                                   requested_players=m_act,
                                                   rebound_type="DREB")]
                stat["answer_location"] = ("m", len(multicond_questions)-1)
            elif stat["type"] == "Ortg":
                multicond_questions += [offensive_rtg_Q(games=g, on_court=on_c, not_on_court=off_c,
                                                        requested_players=m_act)]
                stat["answer_location"] = ("m", len(multicond_questions)-1)
            elif stat["type"] == "Drtg":            
                multicond_questions += [defensive_rtg_Q(games=g, on_court=on_c, not_on_court=off_c,
                                                        requested_players=m_act)]
                stat["answer_location"] = ("m", len(multicond_questions)-1)
                
            elif stat["type"] == "EFG":
                question_methods += [Question.effective_field_goal_percentage]
                stat["answer_location"] = ("q", len(question_methods))
            elif stat["type"] == "TSperc":
                question_methods += [Question.true_shooting_percentage]
                stat["answer_location"] = ("q", len(question_methods))
            elif stat["type"] == "TOrate":
                question_methods += [Question.turnover_rate]
                stat["answer_location"] = ("q", len(question_methods))
            elif stat["type"] == "ASTTOVratio":
                question_methods += [Question.assist_turnover_ratio]
                stat["answer_location"] = ("q", len(question_methods))
                
            else:
                write_error("Unexpected stat name given. " + str(HttpRequest.GET))
                return HttpResponse(json.dumps(False))
        
        Q = Question(games=g, on_court=on_c, not_on_court=off_c, who_made_action=m_act,
                     not_made_action=n_m_act, how_to_calculate=question_methods)
                     
        SO = StatsObject()
        SO.add_games_from_school(school_id)
        question_answers = SO.answer_Questions([Q])[0]
        multicond_answers = SO.answer_Questions(multicond_questions)
        
        answers_in_order = []
        for stat in stats:
            pos = stat["answer_location"][1]
            if stat["answer_location"][0] == "q":
                answer = question_answers[pos]
                if answer == "infinite":
                    answers_in_order += ["Inf."]
                else:
                    answers_in_order += [ "{:.2f}".format(question_answers[pos]) ]
            elif stat["answer_location"][0] == "m":
                if answer == "infinite":
                    answers_in_order += ["Inf."]
                else:
                    answers_in_order += [ "{:.2f}".format(multicond_answers[pos][1]) ]
        return HttpResponse(json.dumps(answers_in_order))
    except Exception as e:
        write_error("Unknown error caught. " + str(HttpRequest.GET))
        return HttpResponse(json.dumps(False))