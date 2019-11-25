import os
from .._exceptions import DelayedImportError
from ._gcloud import _is_gcloud_path
from ._docker import _get_runfile_args, _get_python_command

try:
    import kubernetes as kube
except ImportError:
    kube = DelayedImportError('kubernetes is not installed')
    """
apiVersion: 'batch/v1'
kind: 'Job'
metadata:
  name: '$JOBNAME'
  labels:
    run: '$ITERATION'
spec:
  ttlSecondsAfterFinished: 100
  backoffLimit: 0
  completions: 1
  template:
    metadata:
      labels:
        run: '$ITERATION'
    spec:
      volumes:
      - name: my-secret-vol
        secret:
          secretName: my-secret
      containers:
      - name: 'snakemake'
        image: 'us.gcr.io/vcm-ml/fv3net'
        env:
          - name: GOOGLE_APPLICATION_CREDENTIALS
            value: /secret/key.json
        command: ["python3",  "-m", "fv3net.pipelines.rerun-fv3", "$TIMESTEP"]
        resources:
          requests:
            memory: "3.6G"
          limits:
            memory: "3.6G"
        volumeMounts:
          - name: my-secret-vol
            mountPath: "/secret/"
      restartPolicy: 'Never'
      """


def _ensure_is_remote(location, description):
    if not _is_gcloud_path(location):
        raise ValueError(
            f'{description} must be on Google cloud when running on kubernetes, '
            f'instead is {location}'
        )


def _run_on_kubernetes(
        config_location, outdir, docker_image, runfile=None, jobname=None,
        memory_gb=3.6, memory_gb_limit=None, cpu_count=1, secret_name='my-secret',
    ):
    for location, description in (
            (config_location, 'yaml configuration'),
            (outdir, 'output directory'),
            (runfile, 'runfile')):
        _ensure_is_remote(location, description)
    if memory_gb_limit is None:
        memory_gb_limit = memory_gb
    kube.config.load_kube_config()
    api = kube.client.BatchV1Api()
    job = _create_job_object(config_location, outdir, docker_image, runfile, jobname, memory_gb, memory_gb_limit, cpu_count, secret_name)
    api.create_namespaced_job(body=job, namespace="default")
    # with tempfile.NamedTemporaryFile(suffix='.yaml') as config_tempfile:
    #     bind_mount_args = []
    #     python_args = []
    #     docker_args = []
    #     config_location = _get_config_args(
    #         config_dict_or_location, config_tempfile, bind_mount_args)
    #     _get_docker_args(docker_args, bind_mount_args, outdir)
    #     _get_credentials_args(keyfile, docker_args, bind_mount_args)
    #     _get_runfile_args(runfile, bind_mount_args, python_args)
    #     python_command = [
    #         'python3', '-m', FV3RUN_MODULE, config_location, DOCKER_OUTDIR]
    #     subprocess.check_call(
    #         DOCKER_COMMAND + bind_mount_args + docker_args + [docker_image] +
    #         python_command + python_args)


def _get_kube_command(config_location, runfile=None):
    bind_mount_args = []
    python_args = []
    _get_runfile_args(runfile, bind_mount_args, python_args)
    python_command = _get_python_command(config_location)
    assert bind_mount_args == [], bind_mount_args
    return python_command + python_args


def _create_job_object(
        config_location, outdir, docker_image, runfile, jobname,
        memory_gb, memory_gb_limit, cpu_count, secret_name):
    resource_requirements = kube.client.V1ResourceRequirements(
        limits={
            'memory': f'{memory_gb_limit:.1f}G',
        },
        requests={
            'memory': f'{memory_gb:.1f}G',
            'cpu': f'{cpu_count:.1f}'
        },
    )
    container = kube.client.V1Container(
        name=os.path.basename(docker_image),
        image=docker_image,
        command=_get_kube_command(config_location, outdir, runfile),
        resources=resource_requirements,
        volume_mounts=[
            kube.client.V1VolumeMount(mount_path='/secret/', name='my-secret-vol'),
        ],
        env=[
            kube.client.V1EnvVar(
                name=GOOGLE_APPLICATION_CREDENTIALS, value='/secret/key.json'
            )
        ]
    )
    volume = kube.client.V1Volume(
        name='my-secret-vol',
        secret=kube.client.V1SecretVolumeSource(
            secret_name=secret_name
        )
    )
    pod_spec = kube.client.V1PodSpec(
        restart_policy="Never", containers=[container], volumes=[volume]
    )
    template_spec = kube.client.V1PodTemplateSpec(
        metadata=kube.client.V1ObjectMeta(labels={"app": 'fv3run'}),
        spec=pod_spec,
    )
    job_spec = kube.client.V1JobSpec(
        template=template_spec,
        backoff_limit=0,
        completions=1,
        ttl_seconds_after_finished=100,
    )
    job = kube.client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=kube.client.V1ObjectMeta(
            name=jobname,
            labels={'run': }
        ),
        spec=job_spec,
    )
    return job
