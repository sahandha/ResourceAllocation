from kubernetes import client, config
import sys
import yaml


def create_svc(conf):
    spec = client.V1ServiceSpec(
        selector={'app': conf['app_name']},
        type='NodePort',
        ports=[client.V1ServicePort(
               protocol="TCP",
               port=conf['jlab-port'],
               target_port=conf['target-port'])])
    svc = client.V1Service(
        api_version='v1',
        kind='Service',
        metadata=client.V1ObjectMeta(name=conf['svc_name']),
        spec=spec)
    return svc


def serve(api, service, conf):
    api_r = api.create_namespaced_service(namespace=conf['namespace'], body=service)
    print("Service created. status='%s'" % str(api_r.status))


def create_deploy(conf):
    container_init = client.V1Container(
       name=conf['cont-init-name'],
       image=conf['cont-init-image'],
        env=[
            client.V1EnvVar(name='NB_USER', value='{user}'.format(**conf)),
            client.V1EnvVar(name='NB_PASSWORD', value='{passwd}'.format(**conf)),
            client.V1EnvVar(name='NB_UID', value=conf['cont-uid']),
            client.V1EnvVar(name='NB_GID', value=conf['cont-gid']),
            ],
       args=["/bin/sh", "./pre_lab_work.sh", "/home/{user}".format(**conf)],
       #args=["sleep", "3600"],
       volume_mounts=[
                      client.V1VolumeMount(
                          name=conf['cont-volume'],
                          mount_path='/home/{user}'.format(**conf),
                          sub_path='{user}'.format(**conf)),
                      client.V1VolumeMount(
                          name='repositories',
                          mount_path='/mylist')
                      ],
    )
    container = client.V1Container(
        name=conf['cont-name'],
        image=conf['cont-image'],
        image_pull_policy=conf['cont-policy'],
        lifecycle=client.V1Lifecycle(
                  pre_stop=client.V1Handler(_exec=client.V1ExecAction(
                           command=['rm', '/home/{user}/.desservices.ini'.format(**conf)]))),
        resources=client.V1ResourceRequirements(
                  requests={'memory': conf['cont-mem'], 'cpu': conf['cont-cpu']}),
        env=[
            client.V1EnvVar(name='NB_USER', value='{user}'.format(**conf)),
            client.V1EnvVar(name='NB_UID', value=conf['cont-uid']),
            client.V1EnvVar(name='NB_GID', value=conf['cont-gid']),
            client.V1EnvVar(name='JUPYTER_ENABLE_LAB', value='yes')
            ],
        ports=[client.V1ContainerPort(container_port=conf['jlab-port'])],
        security_context=client.V1SecurityContext(run_as_user=0),
        volume_mounts=[
                      client.V1VolumeMount(
                          name=conf['cont-volume'],
                          mount_path='/home/{user}'.format(**conf),
                          sub_path='{user}'.format(**conf))
                      ],
        args=[
             "start-notebook.sh",
             "--NotebookApp.token='{token}' \
              --NotebookApp.base_url={jlab-url}/{user}".format(**conf)]
        )
    template = client.V1PodTemplateSpec(
               metadata=client.V1ObjectMeta(
                        labels={"app": conf['app_name']}),
               spec=client.V1PodSpec(
                    init_containers=[container_init],
                    containers=[container],
                    automount_service_account_token=False,
                    volumes=[
                             client.V1Volume(
                               name=conf['cont-volume'],
                               persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                                       claim_name=conf['pod-pvc'])),
                             client.V1Volume(
                               name='repositories',
                               config_map=client.V1ConfigMapVolumeSource(name='repositories'))
                            ],
                    hostname=conf['pod-hostname']))
    if conf['extra_volume']:
        vol = client.V1VolumeMount(
              name=conf['job-volume'],
              mount_path='/home/{user}/jobs'.format(**conf))
        mount = client.V1Volume(
                name=conf['job-volume'],
                host_path=client.V1HostPathVolumeSource(
                          path=conf['job-volume-path']+'/'+conf['user']))
        container.volume_mounts.append(vol)
        template.spec.volumes.append(mount)
    spec = client.ExtensionsV1beta1DeploymentSpec(
           replicas=1,
           template=template)
    deployment = client.ExtensionsV1beta1Deployment(
                 api_version="extensions/v1beta1",
                 kind="Deployment",
                 metadata=client.V1ObjectMeta(name=conf['deploy_name']),
                 spec=spec)

    return deployment


def deploy(api, deployment, conf):
    api_r = api.create_namespaced_deployment(
            body=deployment,
            namespace=conf['namespace'])
    print("Deployment created. status='%s'" % str(api_r.status))


def create_ing(conf):
    path = client.V1beta1HTTPIngressPath(
           path='{jlab-url}/{user}'.format(**conf),
           backend=client.V1beta1IngressBackend(
                   service_name=conf['svc_name'],
                   service_port=8888)
           )
    http = client.V1beta1HTTPIngressRuleValue([path])
    spec = client.V1beta1IngressSpec(
           rules=[client.V1beta1IngressRule(http=http)]
            )
    meta = client.V1ObjectMeta(
           name=conf['ing_name'],
           annotations={
                'kubernetes.io/ingress.class': conf['ing-class'],
                'ingress.kubernetes.io/ssl-redirect': 'false'
                 })
    ingress = client.V1beta1Ingress(
              api_version="extensions/v1beta1",
              kind='Ingress',
              metadata=meta,
              spec=spec
              )
    return ingress


def add_ingress_rule(api, ingress, conf):
    api_r = api.create_namespaced_ingress(
            namespace=conf['namespace'],
            body=ingress)
    print("Ingress created. status='%s'" % str(api_r.status))


def main(action='', user='test', token='qwerty', passwd=None):
    try:
        arg = sys.argv[1]
    except:
        arg = action
    try:
        username = sys.argv[2]
    except:
        username = user
    user = username
    with open('conf/config.yaml', 'r') as Fcon:
        conf = yaml.load(Fcon)
    for k in conf['template_names']:
        conf[k] = conf['template_names'][k]+'-{}'.format(user)
    conf['user'] = user
    conf['token'] = token
    conf['passwd'] = passwd

    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()
    if arg == 'deploy':
        api = client.ExtensionsV1beta1Api()
        deployment = create_deploy(conf)
        deploy(api, deployment, conf)
        api_s = client.CoreV1Api()
        svc = create_svc(conf)
        serve(api_s, svc, conf)
        ing = create_ing(conf)
        add_ingress_rule(api, ing, conf)
    elif arg == 'delete':
        api = client.ExtensionsV1beta1Api()
        del_deploy = api.delete_namespaced_deployment(
                     name=conf['deploy_name'],
                     namespace=conf['namespace'],
                     pretty='true',
                     body=client.V1DeleteOptions(
                          propagation_policy="Foreground",
                          grace_period_seconds=1)
                     )
        print(del_deploy)
        del_ing = api.delete_namespaced_ingress(
                  name=conf['ing_name'],
                  namespace=conf['namespace'],
                  pretty='true',
                  body=client.V1DeleteOptions(
                       propagation_policy="Foreground",
                       grace_period_seconds=1)
                  )
        print(del_ing)
        api_s = client.CoreV1Api()
        body = client.V1DeleteOptions(
               propagation_policy="Foreground",
               grace_period_seconds=1)
        del_svc = api_s.delete_namespaced_service(
                  name=conf['svc_name'],
                  namespace=conf['namespace'],
                  body=body,
                  pretty='true')
        print(del_svc)
    elif arg == 'status':
        api = client.CoreV1Api()
        ret = api.list_namespaced_pod(
              watch=False,
              namespace=conf['namespace'],
              label_selector='app={}'.format(conf['app_name']))
        try:
            ready = ret.items[0].status.container_statuses[0].ready
            waiting = ret.items[0].status.container_statuses[0].state.waiting
            if ready is True:
                return 0, 'Running'
            else:
                if waiting:
                    return 2, waiting.reason
                else:
                    return 2, 'Terminating'
        except IndexError:
            return 3, 'Not Running'
    else:
        print('Nothing')


if __name__ == '__main__':
    main()
