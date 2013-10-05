# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import cherrypy
import redis
import time
import random
import json
from Crypto.Cipher import Blowfish
from base64 import b64encode, b64decode
from configparser import ConfigParser

# Dependencies:
# pip install cherrypy redis pycrypto
# yum install redis
# for building pycrypto: yum install python3-devel gmp-devel gcc

class Vote:
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPError(500, "nginx is supposed to serve this.")

    @cherrypy.expose
    def test(self):
        return render('ballot.template',
                      {'x': 'blah', 'usid': 'blah',
                      'id': '{id}', 'name': '{name}'})
    @cherrypy.expose
    def ballot(self, x=None):
        '''Show the ballot page.

        The user has logged in with SCS, and SCS has given us an opaque user
        identifier (in 'x'). Verify this, then issue a usid (associated with 'x'
        in the database). Give them the ballot, including 'x' and the usid.
        '''

        # DEBUG STARTS HERE
        #x = "sdp"
        # DEBUG ENDS HERE
        
        if x is None: raise cherrypy.HTTPError(400)
        x = x.encode('Latin-1') # See cherrypy configuration
        enc_x = b64encode(x).decode('ascii')

        auth_time, auth_user, auth_ip = self.extract_x(x)

        # Check that the current user is probably the same as the one
        # authenticated by SCS by comparing their IP and the current time.
        if time.time() - auth_time > 60:
            print(">> Time mismatch for x={}".format(enc_x))
            raise cherrypy.HTTPError(400, "Try logging in again.")
        if auth_ip != cherrypy.request.headers['X-Real-IP']:
            print(">> IP mismatch for x={}".format(enc_x))
            raise cherrypy.HTTPError(400, "Try logging in again.")

        # Just to avoid confusing people, refuse to show the ballot if they
        # already voted.
        if r.sismember('voted', auth_user):
            raise cherrypy.HTTPError(400, "You already voted.")

        usid = self.register_usid(enc_x)
        return render('ballot.template', {'x': enc_x, 'usid': usid,
                      'id': '{id}', 'name': '{name}'})

    @cherrypy.expose
    def vote(self, usid=None, x=None, **params):
        '''Register a vote, and redirect to success.'''
        if usid is None or x is None: raise cherrypy.HTTPError(400)
        x = x.encode('ascii')

        # Make sure we checked that this person can vote.
        if r.hget('usid', usid) != x:
            raise cherrypy.HTTPError(400, "Try logging in, cheater.")

        auth_time, auth_user, auth_ip = self.extract_x(b64decode(x))

        # Make sure they're still on the same IP -- just in case.
        if auth_ip != cherrypy.request.headers['X-Real-IP']:
            raise cherrypy.HTTPError(400, "Try logging in again.")

        # Mark them as having voted; reject if they're already so marked.
        if r.sadd('voted', auth_user) != 1:
            raise cherrypy.HTTPError(400, "You already voted.")

        # Record the vote!
        r.lpush('votes', json.dumps(params))
        print(json.dumps(params, indent=4))

        raise cherrypy.HTTPRedirect('https://ccss.carleton.ca/election/success')


    def extract_x(self, x):
        '''Extract data from the 'x' value SCS gives us. (x is a bytestring)'''
        # BEGIN DEBUG
        #return time.time(),"simonpratt",cherrypy.request.headers['X-Real-IP']
        # END DEBUG
        
        conf = ConfigParser(interpolation=None)
        conf.read('conf.ini')
        
        scs_shared_key = conf.get('DEFAULT', 'shared_key').encode('ascii')
        scs_iv = conf.get('DEFAULT', 'iv').encode('ascii')
        cipher = Blowfish.new(scs_shared_key, Blowfish.MODE_CBC, scs_iv)
        decrypted = cipher.decrypt(x).decode('utf-8')

        auth_time, user, ip = decrypted.strip('\0').split(' ')
        auth_time = int(getvalue('time=', auth_time))
        user = getvalue('user=', user)
        ip = getvalue('IP=', ip)
        return auth_time, user, ip

    def register_usid(self, x):
        '''Add a user session ID entry, and return the new ID.'''
        success = False
        while not success:
            id = random.randrange(100,1000000)
            success = r.hsetnx('usid', id, x)
        return id

def getvalue(prefix, s):
    if not s.startswith(prefix):
        raise ValueError(repr(s) + "doesn't start with " + repr(prefix))
    return s[len(prefix):]

# Poor-man's templating engine. Because there are too many to choose from.
def render(template, vars):
    with open(template, 'r') as f:
        return f.read().format(**vars)

config = {
    '/': {
        # Say query strings are Latin-1 because we really want bytes.
        # Ugly, but that's what the docs suggest.
        'request.query_string_encoding': 'Latin-1',
        'request.show_tracebacks': False,
    },
    'global': {
        'server.bind_addr': ('127.0.0.1', 5490),
    }
}

r = redis.StrictRedis(unix_socket_path='/run/redis/redis.sock')
cherrypy.quickstart(Vote(), config=config)

