// The namespace.
QB = {};

// Take an array of {id: school_id, value: name} objects and make #teams autocomplete.
QB.make_autocomplete_form = function(schools) {
    var team_autocomplete = $( "#teams" ).autocomplete({
        // Only autocomplete from the beginning of the request term:
        source: function(request, response) {
            var re = $.ui.autocomplete.escapeRegex(request.term);
            var match = new RegExp( "^" + re, "i" );
            var matches = $.grep(schools, function(item, index) {
                return match.test(item.value);
            });
            response(matches);
        },
        // ui.item.id is the school ID, ui.item.value OR window.schools[ui.item.id] is the name.
        select: function(event, ui) {
            QB.school_id = ui.item.id
            QB.get_school_info(ui.item.id);
            /* Clear input - returning false is necessary because the default
               implementation checks for that value before updating the form. */
            $( "#teams" ).val('');
            $( "#team-name" ).text(ui.item.value);
            QB.reset_clickables();
            return false;
        }
    });
    // Same code as source but also make it height-restricted.
    team_autocomplete.autocomplete( "instance" )._renderMenu = function( ul, items ) {
         var that = this;
         $.each( items, function( index, item ) {
             that._renderItemData( ul, item );
         });
         $( ul ).css({"max-height": "400px", "overflow-y": "auto", "overflow-x": "hidden"});
    };
}

/* When a school is selected, fill these divs with school data to be made
   visible when the popup is opened. */ 
QB.populate_divs_with_school_info = function(school_id, games, players) {
    $( "#games-clickable" ).html($("<p>").addClass("param all").attr("data-game-id", "all")
        .text("All games")).prepend($("<p class='popup-title-text'>Games</p>"));
    var all_players_ele = $("<p>").addClass("param all").attr("data-player-id", "all")
        .text("All " + QB.schools[school_id] + " players")
    $( "#on-court-clickable" )          .html(all_players_ele.clone()).prepend($("<p class='popup-title-text'>Players on court</p>"));
    $( "#off-court-clickable" )         .html(all_players_ele.clone()).prepend($("<p class='popup-title-text'>Players off court</p>"));
    $( "#making-actions-clickable" )    .html(all_players_ele.clone()).prepend($("<p class='popup-title-text'>Players making actions</p>"));
    $( "#not-making-actions-clickable" ).html(all_players_ele.clone()).prepend($("<p class='popup-title-text'>Players not making actions</p>"));
    
    $.each(games, function(i, value) {
        game_text = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][value.month-1] +
                    ' ' + value.day + ' ' + value.year + ' ' +
                    (value.is_win ? 'W (' : 'L (') + value.team_score + '-' +
                     value.oppt_score + ') ' + QB.schools[value.oppt_id];
        var ele = $("<p class='param'>").attr("data-game-id", value.game_id)
            .text(game_text);    
        $( "#games-clickable" ).append(ele);
    });

    $.each(players, function(i, value) {
        var ele = $("<p class='param'>").attr("data-player-id", value.player_id)
            .text(value.first + ' ' + value.last +
            (value.title===null ? '' : ' ' + value.title));
        $( "#on-court-clickable" ).append(ele.clone());
        $( "#off-court-clickable" ).append(ele.clone());
        $( "#making-actions-clickable" ).append(ele.clone());
        $( "#not-making-actions-clickable" ).append(ele.clone());
    });
}

// Populate the dropdown autocomplete with school data, set window.schools.
QB.get_schools = function() {
    $.ajax({
        type: "GET",
        url: "/get_schools",
        dataType: "json",
        success: function(data) {
            QB.schools = data;
            array_schools = $.map(data, function(name, school_id) {
                return {id: school_id, value: name};
            });
            QB.make_autocomplete_form(array_schools);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            alert("Failed to load list of schools. Please report this error: " + textStatus + " " + errorThrown);
        }
    });
}

// Given a school ID, get its game and player info.
QB.get_school_info = function(school_id) {
    $.ajax({
        type: "GET",
        url: "/get_school_info/" + school_id,
        dataType: "json",
        success: function(data) {
            QB.games = data.games;
            QB.players = data.players;
            QB.populate_divs_with_school_info(school_id, data.games, data.players);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            alert("Failed to load school info. Please report this error: " + textStatus + " " + errorThrown);
        }
    });
}

QB.make_clickables = function(clickable) {
    $( clickable ).click(function() {
        $( "#popup-content" ).html($( clickable ).html());
        QB.open_pop_up();
        QB.current_clickable = clickable;
        QB.current_close_function = QB.close_pop_up;
    });
}

QB.open_pop_up = function() {
    $( "#popup-container" ).fadeIn(150);
    $( "#background-darkener" ).fadeIn(150);
    $( "#popup-container p.param" ).click(function() {
        $(this).toggleClass("looks-selected-param");
    });
}

QB.simple_close_pop_up = function() {
    $( "#popup-container" ).fadeOut(150);
    $( "#background-darkener" ).fadeOut(150);
}

QB.close_pop_up = function() {
    $( "#popup-container" ).fadeOut(150);
    $( "#background-darkener" ).fadeOut(150);
    /* If a param with class .all is looks-selected, make it looks-selected but
       not is-selected, and vice versa for everything else. */
    if ( $("#popup-content .all").hasClass("looks-selected-param") ) {
        $("#popup-content .param").removeClass("looks-selected-param");
        $("#popup-content .param").addClass("is-selected-param");
        $("#popup-content .all").removeClass("is-selected-param");
        $("#popup-content .all").addClass("looks-selected-param");
    }
    /* Else, make *only* the looks-selected items have is-selected. */
    else {
        $("#popup-content .param").each(function() {
            if ($(this).hasClass("looks-selected-param")) {
                $(this).addClass("is-selected-param");
            }
            else {
                $(this).removeClass("is-selected-param");
            }
        });
    }
    /* Replace the clickable's html with popup-content's html so that when the
       popup is opened again, the same selections will be there. The clickable
       is styled so only .looks-selected-param items show up. */
    $( QB.current_clickable ).html($( "#popup-content" ).html());
}

/* Resetting (getting ready for a new school's information) and deselecting
   (wiping all the question builder's info) should only target the first of
   every ID. Though not the best practice, all these will be duplicated once
   there are calculations done, which .clone() the entire questionbuilder. */
QB.reset_clickables = function() {
    $( "#games-clickable:first" ).empty()
    $( "#on-court-clickable:first" ).empty()
    $( "#off-court-clickable:first" ).empty()
    $( "#making-actions-clickable:first" ).empty()
    $( "#not-making-actions-clickable:first" ).empty()
    // The contents shouldn't change:
    $( "#stat-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
}

QB.deselect_all_items = function() {
    $( "#games-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
    $( "#on-court-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
    $( "#off-court-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
    $( "#making-actions-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
    $( "#not-making-actions-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
    $( "#stat-clickable:first p" ).removeClass("looks-selected-param is-selected-param");
}

QB.calculate = function() {
    if (QB.school_id == null) {
        alert("Select a school first!");
        return;
    }
    $.ajax({
        type: "GET",
        url: "/calculate",
        data: JSON.stringify(QB.collect_question_parameters()),
        contentType: "application/json",
        dataType: "json",
        success: function(data) {
            QB.append_answer(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            alert("Failed to load calculation. Please report this error: " + textStatus + " " + errorThrown);
        }
    });
}

QB.collect_question_parameters = function() {
    function add_id_to_array(arr, source, type_of_id) {
        $( source ).each(function() {
            if($(this).hasClass("is-selected-param")) {
                arr.push($(this).attr(type_of_id));
            }
        });
    }
    
    var games = [];
    var on_court = [];
    var off_court = [];
    var making_actions = [];
    var not_making_actions = [];
    var stats = [];
    add_id_to_array(games,              "#games-clickable:first p",              "data-game-id");
    add_id_to_array(on_court,           "#on-court-clickable:first p",           "data-player-id");
    add_id_to_array(off_court,          "#off-court-clickable:first p",          "data-player-id");
    add_id_to_array(making_actions,     "#making-actions-clickable:first p",     "data-player-id");
    add_id_to_array(not_making_actions, "#not-making-actions-clickable:first p", "data-player-id");
    
    // Stat info is a little different because the Custom stat - turn each into an object.
    $( "#stat-clickable:first p" ).each(function() {
        if($(this).hasClass("is-selected-param")) {
            var stat_type = $(this).attr("data-stat");
            var stat = {"type": stat_type};
            if (stat_type == "Custom") {
                stat.main_stat = $(this).attr("data-main-stat");
                stat.per_what = $(this).attr("data-per-what");
            }
            stats.push(stat);
        }
    });
    
    return {"school_id": QB.school_id, "games": games, "on_court": on_court,
            "off_court": off_court, "making_actions": making_actions,
            "not_making_actions": not_making_actions, "stats": stats}
}

QB.append_answer = function(data) {
    var el_to_append = $( "<div>" ).html($( "#questionbuilder" ).html()).addClass("row");
    var stat_answers = $( "<table>" );
    $( "#stat-clickable:first p.is-selected-param" ).each(function(index) {
        var stat = $( "<td>" ).append($(this).clone());
        var answer = $( "<td>" ).append($( "<p class='answer-text'>" ).text(data[index]));
        var the_row = $("<tr>").append(stat, answer);
        stat_answers.append(the_row);
    });
    $(el_to_append).find( "#stat-clickable" ).html(stat_answers.html());
    $(el_to_append).css("margin-bottom", "60px");
    $( "#questionbuilder" ).after(el_to_append);
}

$(function() {
    var builder_height = $( "#parameter-area" ).outerHeight();
    var title_height = $( "#stats-clickable-title" ).outerHeight();
    $( "#stat-clickable" ).css("min-height", builder_height - title_height - 1);
    
    QB.school_id = null;
    QB.make_clickables("#games-clickable");
    QB.make_clickables("#on-court-clickable");
    QB.make_clickables("#off-court-clickable");
    QB.make_clickables("#making-actions-clickable");
    QB.make_clickables("#not-making-actions-clickable");
    QB.make_clickables("#stat-clickable");
    QB.get_schools();
    
    $( "#calc-button" ).click(function() {
        QB.calculate();
    });
    $( "#reset-button" ).click(function() {
        QB.deselect_all_items();
    });
    $( "#close-button" ).click(function() {
        QB.current_close_function();
    });
    
    $( "#instructions-button" ).click(function() {
        $( "#popup-container" ).fadeIn(150);
        $( "#background-darkener" ).fadeIn(150);
        $( "#popup-content" ).html($("<p class='popup-title-text'>Instructions</p>" +
        "<p class='popup-text'>To begin, select a school. Then click the boxes " +
        "described below to add games and players to each category as appropriate.</p>" +
        "<p class='popup-text'><strong>Games</strong> are the games that will be " +
        "included in statistics calculation.</p>" +
        "<p class='popup-text'><strong>On court</strong> are the players that must " +
        "be on court when an action is made in order for it to count towards a " +
        "calculation.</p>" +
        "<p class='popup-text'><strong>Off court</strong>  are the players that " +
        "must not be on court. (See above.)</p>" +
        "<p class='popup-text'><strong>Making actions</strong>  are the players  " +
        "whose actions are calculated.</p>" +
        "<p class='popup-text'><strong>Not making actions</strong> are the players " +
        "whose actions are not counted. This is only useful in conjunction " +
        "with the 'All players' option for Making actions.</p>" +
        "<p class='popup-text'><strong>Statistics</strong> are the stats " +
        "to calculate with the chosen options.</p>"));
        QB.current_close_function = QB.simple_close_pop_up;
    });
});