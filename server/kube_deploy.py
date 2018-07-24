from __future__ import print_function
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pprint import pprint


def create_namespace(name):
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    api = client.CoreV1Api()

    body = client.V1Namespace(metadata=client.V1ObjectMeta(name=name))
    pretty = 'true'
    try:
        api_response = api.create_namespace(body, pretty=pretty)
        #pprint(api_response)
    except ApiException as e:
        print("Exception when calling CoreV1Api->create_namespace: %s\n" % e)

def create_limitrange(namespace, maxmem="500Mi", maxcpu="999m"):
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    api = client.CoreV1Api()

    body = client.V1LimitRange(
                api_version='v1',
                kind="LimitRange",
                metadata=client.V1ObjectMeta(name=namespace, namespace=namespace),
                spec=client.V1LimitRangeSpec(
                    limits=[
                            client.V1LimitRangeItem(
                                max={"memory":maxmem, "cpu": maxcpu},
                                min={"memory":"100Mi", "cpu" : "100m"},
                                type="Container"
                            )
                    ]
                )
            )
    pretty = 'true'

    try:
        api_response = api.create_namespaced_limit_range(namespace, body, pretty=pretty)
    except ApiException as e:
        print("Exception when calling CoreV1Api->create_namespaced_limit_range: %s\n" % e)

def create_deployment(namespace, name, cpulim, memlim):
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    api = client.ExtensionsV1beta1Api()

    container = client.V1Container(
        name=name,
        image="ansi/lookbusy",
        resources=client.V1ResourceRequirements(
                  requests={'memory': memlim, 'cpu': cpulim}))

    body = client.ExtensionsV1beta1Deployment(
            api_version="extensions/v1beta1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec = client.V1DeploymentSpec(
                selector=client.V1LabelSelector(match_labels={"app":name}),
                template = client.V1PodTemplateSpec(
                       metadata=client.V1ObjectMeta(name=name, namespace=namespace,labels={"app": name}),
                       spec=client.V1PodSpec(containers=[container])
                       )
            )
        )
    pretty = 'true'

    try:
        api_response = api.create_namespaced_deployment(namespace, body, pretty=pretty)
    except ApiException as e:
        pprint("Exception when calling AppsV1Api->create_namespaced_deployment: %s\n" % e)




def delete_namespace(name):
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    api = client.CoreV1Api()

    body = client.V1DeleteOptions()
    pretty = 'true'
    grace_period_seconds = 56
    propagation_policy = "Background"
    try:
        api_response = api.delete_namespace(name, body, pretty=pretty, grace_period_seconds=grace_period_seconds, propagation_policy=propagation_policy)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespace: %s\n" % e)


def delete_deployment(namespace,name):
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    api = client.ExtensionsV1beta1Api()

    body = client.V1DeleteOptions()
    pretty = 'true'
    grace_period_seconds = 56
    propagation_policy = 'Foreground'

    try:
        api_response = api.delete_namespaced_deployment(name, namespace, body, pretty=pretty, grace_period_seconds=grace_period_seconds, propagation_policy=propagation_policy)
        #pprint(api_response)
    except ApiException as e:
        print("Exception when calling ExtensionsV1beta1Api->delete_namespaced_deployment: %s\n" % e)

def main(action='', user='test', token='qwerty', passwd=None):
    print("Call functions directly")


if __name__ == '__main__':
    main()
