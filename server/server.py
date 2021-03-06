import tornado.ioloop
import tornado.web
from tornado.web import asynchronous
import subprocess
import os
from shutil import rmtree
import motor.motor_tornado
from tornado import gen
import kube_deploy as kd
from datetime import datetime, timedelta


__ROOT__     = os.path.join(os.path.dirname(__file__))
__IMAGES__   = os.path.join(os.path.dirname(__file__),"images/")
__UPLOADS__  = os.path.join(os.path.dirname(__file__),"uploads/")
__SCRIPTS__  = os.path.join(os.path.dirname(__file__),"scripts/")
__STATIC__   = os.path.join(os.path.dirname(__file__),"static/")
__TEMPLATE__ = os.path.join(os.path.dirname(__file__),"templates/")
__RESOURCE__ = os.path.join(os.path.dirname(__file__),"resources/")
__USERS__ = os.path.join(os.path.dirname(__file__),"static/users/")
__TotalCPU__ = 3000
__TotalMem__ = 5000

dbhost = "mongodb"
db = motor.motor_tornado.MotorClient(dbhost,27017).ResourceAllocation

@gen.coroutine
def getHardInquiry(db):
    db.system.insert_one({
        'AvailableCPU': __TotalCPU__,
        'AvailableMem': __TotalMem__
    })

@gen.coroutine
def getSystemState(db):

    def cpuReader(str):
        if str.count("m")==0:
            return 1000*float(str)
        else:
            return float(str.strip("m"))
    try:
        api_response=kd.getSystemState()
        nodes = api_response.items
        cpu_available = int(sum([cpuReader(n.status.allocatable["cpu"]) for n in nodes]))
        mem_available = int(0.001*sum([int(n.status.allocatable["memory"].strip('Ki')) for n in nodes]))
        pod_available = sum([int(n.status.allocatable["pods"]) for n in nodes])

        userdata = yield getUserData(db)

        cpu_used= int(sum([float(l[1]) for l in userdata if l[4]=='active']))
        mem_used= int(sum([float(l[2]) for l in userdata if l[4]=='active']))
        pod_used= int(sum([float(l[3]) for l in userdata if l[4]=='active']))

        systemdata = [str(cpu_available), str(cpu_used),
                      str(mem_available), str(mem_used),
                      str(pod_available), str(pod_used)]

    except:
        systemdata = []
    return systemdata

def CreateUser(db, username, userclass, namespace, cpulimit, memlimit, podlimit, timeactive):
    # insert user info into database
    db.users.insert_one({
    'username':username,
    'userclass': userclass,
    'namespace':namespace,
    'cpulimit':cpulimit,
    'memlimit':memlimit,
    'podlimit':podlimit,
    'state':"inactive",
    'activationrequested':'false',
    'jobs':[],
    'expirationdate': datetime.now()+timedelta(minutes=int(timeactive)),
    'timeactive': timeactive
    })

    # Create namespace

    kd.create_namespace(namespace)
    print("namespace has been created")
    kd.create_quota(namespace,priorityclass=userclass)
    print("quota has been created")

@gen.coroutine
def activateuser(db, username):
    doc = yield db.users.find({"username":username},{"_id": 0 ,"namespace": 1, "cpulimit": 1, "memlimit": 1, "podlimit": 1,"userclass":1,"timeactive":1}).to_list(length=1)
    data = doc[0]

    namespace = data["namespace"]
    cpu = data["cpulimit"]
    mem = data["memlimit"]
    pod = data["podlimit"]
    priorityclass = data["userclass"]
    timeactive = data["timeactive"]
    name = namespace

    systemdata = yield getSystemState(db)

    cpufree = float(systemdata[0])-float(systemdata[1])
    memfree = float(systemdata[2])-float(systemdata[3])
    podfree = float(systemdata[4])-float(systemdata[5])

    if (cpufree < float(cpu)) or (cpufree < float(cpu)) or (cpufree < float(cpu)):
        return "Error! Not enough resources available"

    kd.update_quota(name, namespace, maxmem=mem+'Mi', maxcpu=cpu+'m', maxpods=pod, priorityclass=priorityclass)
    expirationdate = datetime.now()+timedelta(minutes=int(timeactive))
    db.users.update_one(
    {'username':username},
    {
        "$set":{
        "state":"active",
        'expirationdate': expirationdate
        }
    })
    kd.create_cronjob(username,namespace,dbhost)
    return "success"

@gen.coroutine
def deactivateuser(db, username):
    doc = yield db.users.find({"username":username},{"_id": 0 ,"namespace": 1}).to_list(length=1)
    data = doc[0]
    namespace = data["namespace"]
    name = namespace


    deleteJob(db, username, "All")

    db.users.update_one(
    {'username':username},
    {
        "$set":{
        "state":"inactive"
        }
    })
    kd.delete_cronjob(namespace)

@gen.coroutine
def submitjob(db,user,jobid,cpulim, memlim, podlim, priority="default"):
    doc = yield db.users.find({'username':user}).to_list(length=1)
    namespace=doc[0]["namespace"]
    jobs=doc[0]["jobs"]
    jobs.append({"jobid":jobid,"cpureq":cpulim,"memreq":memlim,"podreq":podlim})
    if priority == "default":
        priorityclass=doc[0]["userclass"]
    else:
        priotiryclass=priority
    db.users.update_one(
    {'username':user},
    {
        "$set":{
        "jobs":jobs
        }
    })
    kd.create_deployment(namespace, jobid, cpulim+"m", memlim+"Mi", podlim, priorityclass)

@gen.coroutine
def deleteUsers(db, usernames):
    for user in usernames:
        doc = yield db.users.find({"username":user},{"_id": 0 ,"username": 1, "namespace": 1, "state": 1 }).to_list(length=1)
        db.users.delete_one({"username":doc[0]["username"]})
        kd.delete_namespace(doc[0]["namespace"])


@gen.coroutine
def deleteJob(db, user, job):
    doc = yield db.users.find({"username":user},{"_id": 0 ,"username": 1, "namespace": 1, "jobs": 1, "userclass": 1 }).to_list(length=1)
    namespace = doc[0]["namespace"]

    if job == "All":
        kd.namespace_cleanup(namespace) #, priorityclass=class)
        jobs = []
    else:
        kd.delete_deployment(namespace, job)
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
        doc = yield db.users.find({},{"_id": 0 ,"username": 1, "cpulimit": 1, "memlimit": 1, "podlimit": 1, "state": 1, "expirationdate": 1}).to_list(length=100)
        userdata = [[l["username"],l["cpulimit"],l["memlimit"],l["podlimit"],l["state"],str(l["expirationdate"]-datetime.now())] for l in doc]
    except:
        userdata = []
    return userdata

@gen.coroutine
def getJobData(db, user):
    try:
        doc = yield db.users.find({"username":user},{"_id": 0 ,"jobs": 1}).to_list(length=1)
        jobdata = [(l["jobid"], l["cpureq"], l["memreq"], l["podreq"]) for l in doc[0]['jobs']]
    except:
        jobdata = []
    return jobdata

class MainHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            systemdata = yield getSystemState(db)
            userdata   = yield getUserData(db)
            self.render('frontpage.html',
                systemdata=systemdata, userdata=userdata)
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class ConnectToCluster(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            getHardInquiry(db)
            self.redirect('/lsstsim')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class JobManage(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            userdata = yield getUserData(db)

            for user in userdata:
                jobs = yield getJobData(db,user[0])
                cpuavail = str(float(user[1])-sum([float(job[1]) for job in jobs]))
                memavail = str(float(user[2])-sum([float(job[2]) for job in jobs]))
                podavail = str(float(user[3])-sum([float(job[3]) for job in jobs]))

                user.append(jobs)
                user.append(cpuavail)
                user.append(memavail)
                user.append(podavail)
            self.render('LandingPage.html',
                        userdata=userdata)
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class ActivateUser(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            user  = self.get_argument("user")
            message = yield activateuser(db, user)
            if message=='success':
                self.redirect('/lsstsim/jobmanage')
            else:
                self.render('NotFound.html', errormessage="{}".format(message))
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class DeactivateUser(tornado.web.RequestHandler):
    def get(self):
        try:
            user  = self.get_argument("user")
            deactivateuser(db, user)
            self.redirect('/lsstsim')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class JobSubmit(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):

        try:
            user  = self.get_argument("user")
            jobid = self.get_argument(user+"job")
            cpulim=self.get_argument(user+"cpu")
            memlim=self.get_argument(user+"mem")
            podlim=self.get_argument(user+"pod")
            submitjob(db,user,jobid,cpulim,memlim,podlim)
            self.redirect('/lsstsim/jobmanage')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class AddUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            try:
                systemdata = yield getSystemState(db)
                cpumax = float(systemdata[0])-float(systemdata[1])
                cpuval = int(float(systemdata[0])/3)
                cpuval = int(max(cpuval, cpumax/3.))

                memmax = float(systemdata[2])-float(systemdata[3])
                memval = int(float(systemdata[2])/3)
                memval = int(max(memval, memmax/3.))

                podmax = float(systemdata[4])-float(systemdata[5])
                podval = int(float(systemdata[4])/3)
                podval = int(max(podval, podmax/3.))

                limitdata=[str(cpumax), str(cpuval), str(memmax), str(memval), str(podmax), str(podval)]

                #if cpumax <= 0 or memmax <= 0 or podmax <= 0:
                #    self.render('AddUser.html', failmessage="Not enough Resources. User cannot be created.", uri='', limitdata=limitdata)
                #else:
                self.render('AddUser.html', failmessage="", uri='/lsstsim/registeruser', limitdata=limitdata)
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class DeleteUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db)
            users = [l[0] for l in userdata]
            try:
                self.render('DeleteUser.html', users=users, uri='/lsstsim/deleteselectedusers')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class DeleteSelectedUsers(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db)
            users = [l[0] for l in userdata]
            tobedeleted=[]
            try:
                for user in users:
                    try:
                        self.get_argument(user)
                        tobedeleted.append(user)
                    except:
                        pass
                deleteUsers(db, tobedeleted)
                self.redirect('/lsstsim')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class DeleteJob(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        try:
            user  = self.get_argument("username")
            jobid = self.get_argument("jobname")
            deleteJob(db, user, jobid)
            self.redirect('/lsstsim/jobmanage')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class RegistrationHandler(tornado.web.RequestHandler):

    def post(self):
        try:
            username   = self.get_argument('username')
            userclass  = self.get_argument('userclass')
            timeactive = self.get_argument('timeactive')
            namespace  = username+"-ns"
            cpulimit   = self.get_argument('cpulimit')
            memlimit   = self.get_argument('memlimit')
            podlimit   = self.get_argument('podlimit')

            CreateUser(db, username, userclass, namespace, cpulimit, memlimit, podlimit, timeactive)
            self.redirect('/lsstsim')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class NotFoundHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        self.render('NotFound.html', errormessage="not found")

settings=dict(
    template_path=__TEMPLATE__,
    static_path=__STATIC__,
    totalcpu=__TotalCPU__,
    db=db,
    debug=True
)

application = tornado.web.Application([
    (r"/lsstsim/activateuser", ActivateUser),
    (r"/lsstsim/deactivateuser", DeactivateUser),
    (r"/lsstsim/connecttocluster", ConnectToCluster),
    (r"/lsstsim/jobmanage", JobManage),
    (r"/lsstsim/adduser", AddUser),
    (r"/lsstsim/deleteuser", DeleteUser),
    (r"/lsstsim/deleteselectedusers", DeleteSelectedUsers),
    (r"/lsstsim/registeruser", RegistrationHandler),
    (r"/lsstsim/jobsubmit", JobSubmit),
    (r"/lsstsim/jobkill", DeleteJob),
    (r"/lsstsim/projectload(.*)",tornado.web.StaticFileHandler, {"path": "./static"}),
    (r"/lsstsim", MainHandler),
    (r"/lsstsim/.*", NotFoundHandler)
],**settings)

if __name__=="__main__":
    try:
        kd.create_priority_class('privilaged', 1000,)
        kd.create_priority_class('common',     500, default=True)
    except:
        pass
    print("server running at localhost:8888 ...")
    ("press ctrl+c to close.")
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
