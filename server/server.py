import tornado.ioloop
import tornado.web
import subprocess
import os
from shutil import rmtree
import motor.motor_tornado
from tornado import gen



__ROOT__     = os.path.join(os.path.dirname(__file__))
__IMAGES__   = os.path.join(os.path.dirname(__file__),"images/")
__UPLOADS__  = os.path.join(os.path.dirname(__file__),"uploads/")
__SCRIPTS__  = os.path.join(os.path.dirname(__file__),"scripts/")
__STATIC__   = os.path.join(os.path.dirname(__file__),"static/")
__TEMPLATE__ = os.path.join(os.path.dirname(__file__),"templates/")
__RESOURCE__ = os.path.join(os.path.dirname(__file__),"resources/")
__USERS__ = os.path.join(os.path.dirname(__file__),"static/users/")


db1 = motor.motor_tornado.MotorClient().ReourceAllocationCase1
db2 = motor.motor_tornado.MotorClient().ReourceAllocationCase2

def CreateUser(db, username, namespace, email, cpulimit, memlimit):
    # insert user info into database
    db.users.insert_one({
    'username':username,
    'namespace':namespace,
    'email':email,
    'cpulimit':cpulimit,
    'memlimit':memlimit
    })

def DeleteProjectFolder(db, username, project):
    dir = __USERS__+"/"+username+"/"+project
    if os.path.exists(dir):
        rmtree(dir)

@gen.coroutine
def getUsers(db):
    try:
        doc = yield db.users.find({},{"_id": 0 ,"username": 1 }).to_list(length=100)
        users = [l["username"] for l in doc]
    except:
        users = []
    return users



class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('frontpage.html')

class Case1(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        users = yield getUsers(db1)
        try:
            self.render('Case1LandingPage.html',
                        users=users)
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
            users = yield getUsers(db1)
            try:
                self.render('DeleteUser.html',users=users)
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case1RegistrationHandler(tornado.web.RequestHandler):

    def post(self):
        try:
            username  = self.get_argument('username')
            namespace = self.get_argument('namespace')
            email     = self.get_argument('email')
            cpulimit  = self.get_argument('cpulimit')
            memlimit  = self.get_argument('memlimit')
            CreateUser(db1, username, namespace, email, cpulimit, memlimit)
            self.redirect('/case1')
        except Exception as e:
            self.render('AddUser.html',failmessage="User Was not created. {}. Try Again.".format(e))

class Case2(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        try:
            users = yield getUsers(db2)
            self.render('Case2LandingPage.html',
                    users=users)
        except Exception as e:
            self.render('NotFound.html',errormessage="{}".format(e))

class Case2AddUser(tornado.web.RequestHandler):
        def get(self):
            try:
                self.render('AddUser.html', failmessage="", uri='/case2/registeruser')
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))


class Case2DeleteUser(tornado.web.RequestHandler):
        @gen.coroutine
        def get(self):
            users = yield getUsers(db1)
            try:
                self.render('DeleteUser.html',users=users)
            except Exception as e:
                self.render('NotFound.html', errormessage="{}".format(e))

class Case2RegistrationHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            username  = self.get_argument('username')
            namespace = self.get_argument('namespace')
            email     = self.get_argument('email')
            cpulimit  = self.get_argument('cpulimit')
            memlimit  = self.get_argument('memlimit')
            CreateUser(db2, username, namespace, email, cpulimit, memlimit)
            self.redirect('/case2')
        except Exception as e:
            self.render('AddUser.html',failmessage="User Was not created. {}. Try Again.".format(e))

class ForgotPasswordHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('forgot_password.html')

class ProjectLoader(tornado.web.RequestHandler):
    def initialize(self, **configs):
        self.db = self.application.settings['db']
        self.current_user = self.application.settings['current_user']
        self.application.settings['current_project'] = (self.request.uri).lstrip('/projectload')
        self.current_project = self.application.settings['current_project']
        self.projects = self.application.settings['projects']
        staticimages, imagespath, treespath, uploadspath = getPaths(self.current_user, self.current_project)
        self.imagespath = imagespath
        self.staticimages = staticimages

    def get(self):
        self.render('TrainedData.html',
                    username=self.current_user,
                    projects=self.projects,
                    current_project=self.current_project,
                    imagespath=self.static_url(self.staticimages))

class DeleteProject(tornado.web.RequestHandler):
    def initialize(self, **configs):
        self.db = self.application.settings['db']
        current_project = self.application.settings['current_project']
        self.current_user = self.application.settings['current_user']
        projects = self.application.settings['projects']
        projects.remove(current_project)
        self.application.settings['current_project'] = "default"
        self.application.settings['projects'] = projects
        Updatedb(self.current_user,"projects",projects)
        DeleteProjectFolder(self.current_user,current_project)

    def get(self):
        self.redirect('/')

class NewProject(tornado.web.RequestHandler):

    def get(self):
        self.application.settings['current_project'] = "default"
        self.redirect('/')


class ScorePoint(tornado.web.RequestHandler):
    def initialize(self, **configs):
        self.db = self.application.settings['db']
        self.current_user = self.application.settings['current_user']
        self.current_project = self.application.settings['current_project']
        self.projects = self.application.settings['projects']
    def post(self):
        staticimages, imagespath, treespath, uploadspath = getPaths(self.current_user, self.current_project)
        self.staticimages = staticimages
        self.imagespath = imagespath
        datapoint = self.get_argument('datapoint')
        subprocess.call([__SCRIPTS__+'submitsparkjob_scoring.sh',
                         __RESOURCE__+'iso_forest-master.zip',
                         __ROOT__+'/score.py',
                         datapoint,
                         uploadspath,
                         treespath,
                         self.imagespath])
        self.get()
    def get(self):
        self.render("results.html",
                    username=self.current_user,
                    projects=self.projects,
                    current_project=self.current_project,
                    imagespath=self.static_url(self.staticimages))

class ScoreData(tornado.web.RequestHandler):
    def post(self):
        fileinfo = self.request.files['filearg'][0]
        fname = fileinfo['filename']
        extn = os.path.splitext(fname)[1]
        #cname = str(uuid.uuid4()) + extn #this is to scramble the name of the file
        fh = open(uploadspath+"/"+fname, 'wb')
        fh.write(fileinfo['body'])
        fh.close()
        self.redirect('/')

class Upload(tornado.web.RequestHandler):
    def initialize(self, **configs):
        self.db = self.application.settings['db']
        self.current_user = self.application.settings['current_user']
        self.current_project = self.application.settings['current_project']
        self.projects = self.application.settings['projects']


    def post(self):
        project = self.get_argument('projectname')
        if project in self.projects:
            self.render('user_landing_page.html',
                        username=self.current_user,
                        projects=self.projects,
                        current_project=self.current_project,
                        failmessage="Project already exists")
            return
        self.CreateProject(self.current_user,project)
        self.current_project = project
        staticimages, imagespath, treespath, uploadspath = getPaths(self.current_user, self.current_project)
        self.imagespath = imagespath
        self.staticimages = staticimages
        fileinfo = self.request.files['filearg'][0]
        fname = fileinfo['filename']
        cname = 'data.csv'
        fh = open(uploadspath+"/"+cname, 'wb')
        fh.write(fileinfo['body'])
        fh.close()
        subprocess.call([__SCRIPTS__+'submitsparkjob.sh',
                         __RESOURCE__+'iso_forest-master.zip',
                         __ROOT__+'/train.py',
                         uploadspath+"/"+cname,
                         treespath,
                         self.imagespath])
        self.get()
    def get(self):
        self.redirect("/projectload"+self.current_project)

    def CreateProject(self,username,project):
        projectdir = __USERS__+"/"+username+"/"+project
        useruploads=projectdir+"/uploads"
        if not os.path.exists(useruploads):
            os.makedirs(useruploads)

        userimages=projectdir+"/images"
        if not os.path.exists(userimages):
            os.makedirs(userimages)

        usertrees=projectdir+"/trees"
        if not os.path.exists(usertrees):
            os.makedirs(usertrees)

        self.application.settings["current_project"] = project
        self.projects.append(project)
        self.application.settings['projects'] = self.projects
        Updatedb(self.current_user,'projects', self.projects)
        #putPaths(self.current_user, project)

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
    (r"/case1/registeruser", Case1RegistrationHandler),
    (r"/case2", Case2),
    (r"/case2/adduser", Case2AddUser),
    (r"/case2/deleteuser", Case2DeleteUser),
    (r"/case2/registeruser", Case2RegistrationHandler),
    (r"/projectload(.*)",tornado.web.StaticFileHandler, {"path": "./static"}),
    (r"/", MainHandler)
],**settings)

if __name__=="__main__":
    print("server running at localhost:8888 ...")
    print("press ctrl+c to close.")
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
