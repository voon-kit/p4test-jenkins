pipeline {
    agent any
    parameters {
        string(name: 'STREAM', description: "Name of stream")
        string(name: 'CHANGELIST', description: "Changelist number of AMI to retrieve source code from")
    }
    stages {
        stage('Build') {
            steps {
                sh "echo ${params.STREAM} ${params.CHANGELIST}"
                sh "python3 updateAMI.py --STREAM ${params.STREAM} --CHANGELIST ${params.CHANGELIST} --BUILDSTATUS BUILDING -c --rt-port 6289 --server-address flux.3forge.net"
                buildName "#${env.BUILD_NUMBER}: ${params.STREAM} @${params.CHANGELIST}"
                echo 'OK!!'
                sleep(time: 30, unit: 'SECONDS') //simulate building time of 30 seconds
                //error("test error message") //uncomment to hit build error
            }
        }
    }
    post {
        always{
            sh "python3 updateAMI.py --STREAM ${params.STREAM} --CHANGELIST ${params.CHANGELIST} --BUILDSTATUS ${currentBuild.currentResult} -c --rt-port 6289 --server-address flux.3forge.net"
        }
    }
}