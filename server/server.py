import tornado.ioloop
import tornado.web
import subprocess
import os
from shutil import rmtree
import motor.motor_tornado
from tornado import gen
import kube_deploy as kd


__ROOT__     = os.path.join(os.path.dirname(__file__))
__IMAGES__   = os.path.join(os.path.dirname(__file__),"images/")
__UPLOADS__  = os.path.join(os.path.dirname(__file__),"uploads/")
__SCRIPTS__  = os.path.join(os.path.dirname(__file__),"scripts/")
__STATIC__   = os.path.join(os.path.dirname(__file__),"static/")
__TEMPLATE__ = os.path.join(os.path.dirname(__file__),"templates/")
__RESOURCE__ = os.path.join(os.path.dirname(__file__),"resources/")
__USERS__ = os.path.join(os.path.dirname(__file__),"static/users/")


db1 = motor.motor_tornado.MotorClient().ResourceAllocationCase1
db2 = motor.motor_tornado.MotorClient().ResourceAllocationCase2

def CreateUser1(db, username, namespace, cpulimit, memlimit):
    # insert user info into database
    db.users.insert_one({
    'username':username,
    'namespace':namespace,
    'cpulimit':cpulimit,
    'memlimit':memlimit,
    'jobs':[]
    })

    # Create namespace
    kd.create_namespace(namespace)
    kd.create_limitrange(namespace, maxmem=memlimit+'Mi', maxcpu=cpulimit+'m')

def CreateUser2(db, username, cpulimit, memlimit):
    # insert user info into database
    db.users.insert_one({
    'username':username,
    'cpulimit':cpulimit,
    'memlimit':memlimit,
    'jobs':[]
    })

@gen.coroutine
def submitjob1(db,user,jobid,cpulim, memlim):
    doc = yield db.users.find({'username':user}).to_list(length=1)
    namespace=doc[0]["namespace"]
    jobs=doc[0]["jobs"]
    jobs.append({"jobid":jobid,"cpureq":cpulim,"memreq":memlim})

    db.users.update_one(
    {'username':user},
    {
        "$set":{
        "jobs":jobs
        }
    })
    kd.create_deployment(namespace, jobid, cpulim+"m", memlim+"Mi")

@gen.coroutine
def submitjob2(db,user,jobid,cpureq, memreq):
    doc = yield db.users.find({'username':user}).to_list(length=1)
    cpulim=doc[0]["cpulimit"]
    memlim=doc[0]["memlimit"]
    namespace = user+jobid+"-ns"
    kd.create_namespace(namespace)
    kd.create_limitrange(namespace, maxmem=memlim+'Mi', maxcpu=cpulim+'m')
    kd.create_deployment(namespace, jobid, cpureq+"m", memreq+"Mi")

    jobs=doc[0]["jobs"]
    jobs.append({"jobid":jobid,"cpureq":cpulim,"memreq":memlim})

    db.users.update_one(
    {'username':user},
    {
        "$set":{
        "jobs":jobs
        }
    })

@gen.coroutine
def DeleteUsers1(db, usernames):
    for user in usernames:
        doc = yield db.users.find({"username":user},{"_id": 0 ,"username": 1, "namespace": 1 }).to_list(length=1)
        db.users.delete_one({"username":doc[0]["username"]})
        kd.delete_namespace(doc[0]["namespace"])

@gen.coroutine
def DeleteJob1(db, user, job):
    doc = yield db.users.find({"username":user},{"_id": 0 ,"username": 1, "namespace": 1, "jobs": 1 }).to_list(length=1)
    namespace = doc[0]["namespace"]
    jobs=doc[0]["jobs"]
    jobs = [x for x in jobs if x['jobid'] != job]
    db.users.update_one(
    {'username':user},
    {
        "$set":{
        "jobs":jobs
        }
    })
    kd.delete_deployment(namespace, job)

@gen.coroutine
def DeleteUsers2(db, usernames):
    for user in usernames:
        doc = yield db.users.find({"username":user},{"_id": 0 ,"username": 1, "jobs":1}).to_list(length=1)
        username = doc[0]["username"]
        jobs = doc[0]["jobs"]
        db.users.delete_one({"username":username})
        for job in jobs:
            jobns = username+job["jobid"]+'-ns'
            kd.delete_namespace(jobns)

@gen.coroutine
def DeleteJob2(db,user,job): # TODO: need to complete this
    doc = yield db.users.find({"username":user},{"_id": 0 , "jobs": 1 }).to_list(length=1)
    kd.delete_namespace(job+'-ns')

    jobs=doc[0]["jobs"]
    jobs = [x for x in jobs if x['jobid'] != job]

    db.users.update_one(
    {'username':user},
    {
        "$set":{
        "jobs":jobs
        }
    })

@gen.coroutine
def getUserData(db):
    try:
        doc = yield db.users.find({},{"_id": 0 ,"username": 1, "cpulimit": 1, "memlimit": 1 }).to_list(length=100)
        userdata = [[l["username"],l["cpulimit"],l["memlimit"]] for l in doc]
    except:
        userdata = []
    return userdata

@gen.coroutine
def getJobData(db, user):
    try:
        doc = yield db.users.find({"username":user},{"_id": 0 ,"jobs": 1}).to_list(length=1)
        jobdata = [(l["jobid"], l["cpureq"], l["memreq"]) for l in doc[0]['jobs']]
    except:
        jobdata = []
    return jobdata


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('frontpage.html')

class Case1(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            userdata = yield getUserData(db1)
            for user in userdata:
                jobs = yield getJobData(db1,user[0])
                user.append(jobs)
            self.render('Case1LandingPage.html',
                        userdata=userdata)
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class Case1JobSubmit(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):

        try:
            user  = self.get_argument("user")
            jobid = self.get_argument(user+"job")
            cpulim=self.get_argument(user+"cpu")
            memlim=self.get_argument(user+"mem")
            submitjob1(db1,user,jobid,cpulim,memlim)
            self.redirect('/case1')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class Case1AddUser(tornado.web.RequestHandler):
        def get(self):
            try:
                self.render('AddUser.html', failmessage="", uri='/case1/registeruser')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case1DeleteUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db1)
            users = [l[0] for l in userdata]
            try:
                self.render('DeleteUser.html', users=users, uri='/case1/deleteselectedusers')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case1DeleteSelectedUsers(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db1)
            users = [l[0] for l in userdata]
            tobedeleted=[]
            try:
                for user in users:
                    try:
                        self.get_argument(user)
                        tobedeleted.append(user)
                    except:
                        pass
                DeleteUsers1(db1, tobedeleted)
                self.redirect('/case1')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case1DeleteJob(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        try:
            user  = self.get_argument("username")
            jobid = self.get_argument("jobname")
            DeleteJob1(db1, user, jobid)
            self.redirect('/case1')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class Case1RegistrationHandler(tornado.web.RequestHandler):

    def post(self):
        try:
            username  = self.get_argument('username')
            namespace = self.get_argument('namespace')
            cpulimit  = self.get_argument('cpulimit')
            memlimit  = self.get_argument('memlimit')
            CreateUser1(db1, username, namespace, cpulimit, memlimit)
            self.redirect('/case1')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class Case2(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            userdata = yield getUserData(db2)
            for user in userdata:
                jobs = yield getJobData(db2,user[0])
                user.append(jobs)
            self.render('Case2LandingPage.html',
                    userdata=userdata)
        except Exception as e:
            self.render('NotFound.html',errormessage="{}".format(e))

class Case2JobSubmit(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        try:
            user  = self.get_argument("user")
            jobid = self.get_argument(user+"job")
            cpureq=self.get_argument(user+"cpu")
            memreq=self.get_argument(user+"mem")
            submitjob2(db2,user,jobid,cpureq,memreq)
            self.redirect('/case2')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))


class Case2AddUser(tornado.web.RequestHandler):
        def get(self):
            try:
                self.render('Case2AddUser.html', failmessage="", uri='/case2/registeruser')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case2DeleteUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db2)
            users = [l[0] for l in userdata]
            try:
                self.render('DeleteUser.html',users=users, uri='/case2/deleteselectedusers')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case2DeleteSelectedUsers(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db2)
            users = [l[0] for l in userdata]
            tobedeleted=[]
            try:
                for user in users:
                    try:
                        self.get_argument(user)
                        tobedeleted.append(user)
                    except:
                        pass
                DeleteUsers2(db2, tobedeleted)
                self.redirect('/case2')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case2DeleteJob(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        try:
            user  = self.get_argument("username")
            jobid = self.get_argument("jobname")
            DeleteJob2(db2, user, jobid)
            self.redirect('/case2')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))


class Case2RegistrationHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            username  = self.get_argument('username')
            cpulimit  = self.get_argument('cpulimit')
            memlimit  = self.get_argument('memlimit')
            CreateUser2(db2, username, cpulimit, memlimit)
            self.redirect('/case2')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

settings=dict(
    template_path=__TEMPLATE__,
    static_path=__STATIC__,
    users_path=__USERS__,
    current_user='no_user',
    projects=[],
    current_project='default',
    db1=db1,
    db2=db2,
    users=[],
    debug=True
)

application = tornado.web.Application([
    (r"/case1", Case1),
    (r"/case1/adduser", Case1AddUser),
    (r"/case1/deleteuser", Case1DeleteUser),
    (r"/case1/deleteselectedusers", Case1DeleteSelectedUsers),
    (r"/case1/registeruser", Case1RegistrationHandler),
    (r"/case1/jobsubmit", Case1JobSubmit),
    (r"/case1/jobkill", Case1DeleteJob),
    (r"/case2", Case2),
    (r"/case2/adduser", Case2AddUser),
    (r"/case2/deleteuser", Case2DeleteUser),
    (r"/case2/deleteselectedusers", Case2DeleteSelectedUsers),
    (r"/case2/registeruser", Case2RegistrationHandler),
    (r"/case2/jobsubmit", Case2JobSubmit),
    (r"/case2/jobkill", Case2DeleteJob),
    (r"/projectload(.*)",tornado.web.StaticFileHandler, {"path": "./static"}),
    (r"/", MainHandler)
],**settings)

if __name__=="__main__":
    print("server running at localhost:8888 ...")
    print("press ctrl+c to close.")
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
