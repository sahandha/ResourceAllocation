import tornado.ioloop
import tornado.web
import subprocess
import os
from shutil import rmtree
import motor.motor_tornado
from tornado import gen
import kube_deploy as kd
from datetime import datetime


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


db = motor.motor_tornado.MotorClient().ResourceAllocation

@gen.coroutine
def getHardInquiry(db):
    db.system.insert_one({
        'AvailableCPU': __TotalCPU__,
        'AvailableMem': __TotalMem__
    })

@gen.coroutine
def getSystemState(db):
    try:
        api_response=kd.getSystemState()
        nodes = api_response.items
        cpu_available = int(sum([float(n.status.allocatable["cpu"].strip('m')) for n in nodes]))
        mem_available = int(0.001*sum([int(n.status.allocatable["memory"].strip('Ki')) for n in nodes]))
        pod_available = sum([int(n.status.allocatable["pods"]) for n in nodes])

        userdata = yield getUserData(db)

        cpu_used= int(sum([float(l[1]) for l in userdata]))
        mem_used= int(sum([float(l[2]) for l in userdata]))
        pod_used= int(sum([float(l[3]) for l in userdata]))

        systemdata = [str(cpu_available), str(cpu_used),
                      str(mem_available), str(mem_used),
                      str(pod_available), str(pod_used)]

    except:
        systemdata = []
    return systemdata

def CreateUser(db, username, namespace, cpulimit, memlimit, podlimit):
    # insert user info into database
    db.users.insert_one({
    'username':username,
    'namespace':namespace,
    'cpulimit':cpulimit,
    'memlimit':memlimit,
    'podlimit':podlimit,
    'jobs':[],
    'timecreated': str(datetime.now())
    })

    # Create namespace
    kd.create_namespace(namespace)
    kd.create_quota(namespace, maxmem=memlimit+'Mi', maxcpu=cpulimit+'m', maxpods=podlimit)

@gen.coroutine
def submitjob(db,user,jobid,cpulim, memlim, podlim):
    doc = yield db.users.find({'username':user}).to_list(length=1)
    namespace=doc[0]["namespace"]
    jobs=doc[0]["jobs"]
    jobs.append({"jobid":jobid,"cpureq":cpulim,"memreq":memlim,"podreq":podlim})

    db.users.update_one(
    {'username':user},
    {
        "$set":{
        "jobs":jobs
        }
    })
    kd.create_deployment(namespace, jobid, cpulim+"m", memlim+"Mi", podlim)

@gen.coroutine
def deleteUsers(db, usernames):
    for user in usernames:
        doc = yield db.users.find({"username":user},{"_id": 0 ,"username": 1, "namespace": 1 }).to_list(length=1)
        db.users.delete_one({"username":doc[0]["username"]})
        kd.delete_namespace(doc[0]["namespace"])

@gen.coroutine
def deleteJob(db, user, job):
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
def getUserData(db):
    try:
        doc = yield db.users.find({},{"_id": 0 ,"username": 1, "cpulimit": 1, "memlimit": 1, "podlimit": 1, "timecreated": 1}).to_list(length=100)
        userdata = [[l["username"],l["cpulimit"],l["memlimit"],l["podlimit"],l["timecreated"]] for l in doc]
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
            self.redirect('/')
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
            self.redirect('/jobmanage')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class AddUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            try:
                systemdata = yield getSystemState(db)
                print(systemdata)
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

                if cpumax <= 0 or memmax <= 0 or podmax <= 0:
                    self.render('AddUser.html', failmessage="Not enough Resources. User cannot be created.", uri='', limitdata=limitdata)
                else:
                    self.render('AddUser.html', failmessage="", uri='/registeruser', limitdata=limitdata)
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class DeleteUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            userdata = yield getUserData(db)
            users = [l[0] for l in userdata]
            try:
                self.render('DeleteUser.html', users=users, uri='/deleteselectedusers')
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
                self.redirect('/')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class DeleteJob(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        try:
            user  = self.get_argument("username")
            jobid = self.get_argument("jobname")
            deleteJob(db, user, jobid)
            self.redirect('/jobmanage')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

class RegistrationHandler(tornado.web.RequestHandler):

    def post(self):
        try:
            username  = self.get_argument('username')
            namespace = username+"-ns"
            cpulimit  = self.get_argument('cpulimit')
            memlimit  = self.get_argument('memlimit')
            podlimit  = self.get_argument('podlimit')
            CreateUser(db, username, namespace, cpulimit, memlimit, podlimit)
            self.redirect('/')
        except Exception as e:
            self.render('NotFound.html', errormessage="{}".format(e))

settings=dict(
    template_path=__TEMPLATE__,
    static_path=__STATIC__,
    users_path=__USERS__,
    current_user='no_user',
    totalcpu=__TotalCPU__,
    db=db,
    debug=True
)

application = tornado.web.Application([
    (r"/connecttocluster", ConnectToCluster),
    (r"/jobmanage", JobManage),
    (r"/adduser", AddUser),
    (r"/deleteuser", DeleteUser),
    (r"/deleteselectedusers", DeleteSelectedUsers),
    (r"/registeruser", RegistrationHandler),
    (r"/jobsubmit", JobSubmit),
    (r"/jobkill", DeleteJob),
    (r"/projectload(.*)",tornado.web.StaticFileHandler, {"path": "./static"}),
    (r"/", MainHandler)
],**settings)

if __name__=="__main__":
    print("server running at localhost:8888 ...")
    print("press ctrl+c to close.")
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
