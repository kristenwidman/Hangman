#!/usr/bin/env python

#kristenwidman
#June 18, 2013

#Hangman!

import json
import requests
import os.path
import re
import cgi
import urllib
import webapp2
import jinja2
from google.appengine.ext import ndb

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'])
BASE_URL = "http://hangman.coursera.org/hangman/game"

def game_db_key(game_key):
    '''creates a parent key for all datastore entries.
        The parent will be the game key.
    '''
    return ndb.Key('Game', game_key)

class Letter(ndb.Model):
    '''Defines a model for the letter to be stored'''
    letter = ndb.StringProperty()

class StartGame(webapp2.RequestHandler):

    def write_form(self, template_values):
        '''Convenience function to write template'''
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.out.write(template.render(template_values))

    def get(self):
        '''upon loading page through a 'get', write template'''
        template_values = {'errors':'',}
        self.write_form(template_values)

    def post(self):
        '''upon loading page through a 'post':
            validate email, rewrite page if errors present,
            send post request to api if not, parse json data received,
            redirect to next url.
        '''
        email = cgi.escape(self.request.get('email'))
        errors = self.validate_email(email)
        if errors != '':
            template_values = {'errors':errors,}
            self.write_form(template_values)
        else:
            payload = {"email": email}
            r = requests.post(BASE_URL, data=json.dumps(payload))
            js = r.json()
            key = js['game_key']
            params = {'key':key}
            new_url = '/guess?' + urllib.urlencode(params)
            self.redirect(new_url)

    def validate_email(self, email):
        '''Compares email to regex (not perfect, but pretty good).
            Will return an error if email does not match.
        '''
        errors = ''
        email_regex = re.compile(r"^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")
        if email == u'':
            errors += "Please enter an email address to start playing"
        elif not email_regex.match(email):
            errors += "Please enter a valid email. You entered %s.\n" %(email)
        return errors

class Guess(webapp2.RequestHandler):

    def write_form(self,template_values):
        '''Convenience function to write template'''
        template = JINJA_ENVIRONMENT.get_template('templates/guess.html')
        self.response.out.write(template.render(template_values))

    def get(self):
        '''upon page load from a 'get' request, gets game key
            and writes template
        '''
        key = cgi.escape(self.request.get('key'))
        template_values = {
                'key': key,
                'errors': '',
                'phrase': '',
                'tries_left': '',
        }
        self.write_form(template_values)

    def post(self):
        '''upon page load from a 'post' request, pulls needed values
            from template, validates letter input from user. Checks if
            letter has been guessed before. If there are errors,
            re-writes template with errors without processing letter.
            If good, sends post request to API, parses new values,
            checks for winning and losing states, and writes
            appropriate template.
        '''
        key = cgi.escape(self.request.get('key'))
        letter = cgi.escape(self.request.get('letter'))
        phrase = cgi.escape(self.request.get('phrase'))
        state = cgi.escape(self.request.get('state'))
        tries_left = cgi.escape(self.request.get('tries_left'))
        errors = self.validate_letter(letter)
        if errors == '':
            used_letters_query = Letter.query(ancestor=game_db_key(key))
            letters = used_letters_query.fetch(26)
            for used_letter in letters:
                if used_letter.letter == letter:
                    errors = "You already picked letter %s. Please guess a different letter" % (letter)
                    return self.write_page(key, errors, phrase, tries_left)
            payload = {"guess": letter}
            r = requests.post(os.path.join(BASE_URL, key), data=json.dumps(payload))
            if r.status_code == requests.codes.ok:
                js = r.json()
                tries_left = str(int(js['num_tries_left']) + 1) #0 based indexing to 1
                phrase = js['phrase']
                state = js['state']
                used_letter = Letter(parent=game_db_key(key))
                used_letter.letter = letter
                used_letter.put() #store letter in datastore
                if state == "won":
                    params = {'phrase':phrase}
                    new_url = '/won?' + urllib.urlencode(params)
                    self.redirect(new_url)
                elif state == "lost" or tries_left < 0:
                    self.redirect('/lost')
            elif r.status_code == 400:
                js = r.json()
                errors = js['error']
            else:
                r.raise_for_status()
                #TODO: do something with this?
        self.write_page(key, errors, phrase, tries_left)

    def write_page(self, key, errors, phrase, tries_left):
        '''convenience method for writing template'''
        template_values = {
                'key': key,
                'errors': errors,
                'phrase': phrase,
                'tries_left': tries_left,
        }
        self.write_form(template_values)

    def validate_letter(self,letter):
        '''validates that input is a single letter'''
        errors = ''
        letter_regex = re.compile(r"^[a-zA-Z]$")
        if letter == u'':
            errors += "Please enter a letter to play."
        elif not letter_regex.match(letter):
            errors += "Please enter a valid single letter, upper or lower case. You entered '%s'.\n" %(letter)
        return errors

class Won(webapp2.RequestHandler):

    def get(self):
        phrase = cgi.escape(self.request.get('phrase'))
        template_values = {
                'phrase': phrase,
        }
        template = JINJA_ENVIRONMENT.get_template('templates/won.html')
        self.response.out.write(template.render(template_values))


class Lost(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/lost.html')
        self.response.out.write(template.render())

class Goodbye(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/goodbye.html')
        self.response.out.write(template.render())


app = webapp2.WSGIApplication([('/', StartGame),
                                ('/guess', Guess),
                                ('/won', Won),
                                ('/lost', Lost),
                                ('/goodbye', Goodbye)],
                                debug=False)
