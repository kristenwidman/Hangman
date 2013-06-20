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

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'])
BASE_URL = "http://hangman.coursera.org/hangman/game"
DEBUG = True

class StartGame(webapp2.RequestHandler):

    def write_form(self, template_values):
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.out.write(template.render(template_values))

    def get(self):
        template_values = {'errors':'',}
        self.write_form(template_values)

    def post(self):
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
            if DEBUG:
                print 'url: ', r.url
                print 'status', r.status_code
                print 'json',js
                print 'key type', type(key)
                print 'new url redirect to:', new_url
            self.redirect(new_url)

    def validate_email(self, email):
        errors = ''
        email_regex = re.compile(r"^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")
        if email == u'':
            errors += "Please enter an email address to start playing"
        elif not email_regex.match(email):
            errors += "Please enter a valid email. You entered %s.\n" %(email)
        if DEBUG: print errors
        return errors

class Guess(webapp2.RequestHandler):

    def write_form(self,template_values):
        template = JINJA_ENVIRONMENT.get_template('templates/guess.html')
        self.response.out.write(template.render(template_values))

    def get(self):
        key = cgi.escape(self.request.get('key'))
        if DEBUG: print 'from Guess, key:',key
        template_values = {
                'key': key,
                'errors': '',
                'phrase': '',
                'tries_left': '',
        }
        self.write_form(template_values)

    def post(self):
        print 'request arguments:',self.request.arguments()
        key = cgi.escape(self.request.get('key'))
        letter = cgi.escape(self.request.get('letter'))
        phrase = cgi.escape(self.request.get('phrase'))
        state = cgi.escape(self.request.get('state'))
        tries_left = cgi.escape(self.request.get('tries_left'))
        errors = self.validate_letter(letter)
        print '1st time: ', key, letter, errors, phrase, tries_left
        if errors == '':
            payload = {"guess": letter}
            r = requests.post(os.path.join(BASE_URL, key), data=json.dumps(payload))
            if r.status_code == requests.codes.ok:
                js = r.json()
                tries_left = js['num_tries_left']
                phrase = js['phrase']
                state = js['state']
                if DEBUG:
                    print 'status', r.status_code
                    print 'json: ',js
                if state == "won":
                    params = {'phrase':phrase}
                    new_url = '/won?' + urllib.urlencode(params)
                    self.redirect(new_url)
            elif r.status_code == 400:
                js = r.json()
                errors = js['error']
            else:
                r.raise_for_status()
                #TODO: do something with this?
        template_values = {
                'key': key,
                'errors': errors,
                'phrase': phrase,
                'tries_left': tries_left,
        }
        if DEBUG: print key, errors, phrase, tries_left
        self.write_form(template_values)

    def validate_letter(self,letter):
        errors = ''
        letter_regex = re.compile(r"^[a-zA-Z]$")
        if letter == u'':
            errors += "Please enter a letter to play."
        elif not letter_regex.match(letter):
            errors += "Please enter a valid single letter, upper or lower case. You entered '%s'.\n" %(letter)
        if DEBUG: print errors
        return errors

class Won(webapp2.RequestHandler):

    def get(self):
        phrase = cgi.escape(self.request.get('phrase'))
        template_values = {
                'phrase': phrase,
        }
        template = JINJA_ENVIRONMENT.get_template('templates/won.html')
        self.response.out.write(template.render(template_values))



app = webapp2.WSGIApplication([('/', StartGame),
                                ('/guess', Guess),
                                ('/won', Won)],
                                debug=DEBUG)
