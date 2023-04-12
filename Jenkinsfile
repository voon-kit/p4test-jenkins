pipeline {
    agent any
    parameters {
        string(name: 'STREAM', description: "Name of stream")
        string(name: 'CHANGELIST', description: "Changelist number of AMI to retrieve source code from")
    }
    stages {
        stage('Build') {
            steps {
                bat "py updateAMI.py --STREAM ${STREAM} --CHANGELIST ${CHANGELIST} --BUILDSTATUS BUILDING -c --rt-port 3289 --server-address localhost"
                buildName "#${BUILD_NUMBER}: ${STREAM} @${CHANGELIST}"
                echo 'OK!!'
                sleep(time: 30, unit: 'SECONDS') //simulate building time of 30 seconds
                //error("test error message") //uncomment to hit build error
            }
        }
    }
    post {
        always{
            sh "python updateAMI.py --STREAM ${STREAM} --CHANGELIST ${CHANGELIST} --BUILDSTATUS ${currentBuild.currentResult} -c --rt-port 3289 --server-address localhost"
        }
    }
}