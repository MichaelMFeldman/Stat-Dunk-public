from django import forms

class QuestionBuilderForm(forms.Form):
    question = forms.CharField(max_length=2048)