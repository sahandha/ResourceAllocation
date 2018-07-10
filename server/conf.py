###### NAMES ######
#user: 'test'
namespace: 'default'
template_names:
  svc_name: 'jlab-svc'
  deploy_name: 'jlab-deploy'
  app_name: 'jlab-app'
  ing_name: 'jlab-ing'
###### SERVICE ######
jlab-port: 8888
target-port: 8888
jlab-url: '/portal/labs' #'/easyweb/deslabs/labs' #/portal/labs
ing-class: 'nginx' #'internal' #nginx
###### CONTAINER ######
cont-name: 'jlab'
cont-image: 'jupyter/base-notebook'
cont-init-name: 'lab-init'
cont-init-image: 'mgckind/lab-init:1.0.4'
cont-policy: 'Always' #IfNotPresent
cont-volume: 'jlab-volume'
cont-uid: '1001' #'1000'
cont-gid: '1001' #'100'
cont-mem: '1024Mi'
cont-cpu: '1000m'
pod-pvc: 'jlab-pvc'
pod-hostname: 'deslabs'

###### VOLUMES ######
extra_volume: False
job-volume: 'jlab-jobs'
job-volume-path: '/des004/despublic_scratch/workdir'
