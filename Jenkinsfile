@Library('jenkins-helpers') _

def label = "python-pytest-parallel-${UUID.randomUUID().toString().substring(0, 5)}"

podTemplate(label: label,
            annotations: [podAnnotation(key: "jenkins/build-url", value: env.BUILD_URL ?: ""),
                          podAnnotation(key: "jenkins/github-pr-url", value: env.CHANGE_URL ?: "")],
            containers: [containerTemplate(name: 'python',
                                           image: 'python:3.6.6',
                                           command: '/bin/cat -',
                                           resourceRequestCpu: '1000m',
                                           resourceRequestMemory: '1000Mi',
                                           resourceLimitCpu: '1000m',
                                           resourceLimitMemory: '1000Mi',
                                           envVars: [envVar(key: 'PYTHONPATH', value: '/usr/local/bin'),
                                                     envVar(key: 'PIP_CONFIG_FILE', value: '/pip/pip.conf')],
                                           ttyEnabled: true)],
            volumes: [secretVolume(secretName: 'pypi-artifactory-credentials', mountPath: '/pip', readOnly: true)],
            envVars: [secretEnvVar(key: 'PYPI_ARTIFACTORY_URL', secretName: 'pypi-artifactory-credentials', secretKey: 'pypiurl')]) {
    node(label) {
        container('jnlp') {
            checkout(scm)
        }
        container('python') {
            stage('Install dependencies') {
                sh('python setup.py install')
                sh('pip install pytest mock')
            }
            stage('Test') {
                withEnv(['PYTHONDONTWRITEBYTECODE=1']) {
                    sh('pytest tests')
                }
            }
            stage('Build') {
                sh('python setup.py build')
            }
            if (env.BRANCH_NAME == 'master') {
                stage('Publish') {
                    withEnv(['HOME=/pip']) {
                        sh('python setup.py register -r artifactory')
                        sh('python setup.py sdist upload -r artifactory')
                    }
                }
            }
        }
    }
}