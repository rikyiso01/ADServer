FROM docker.io/ensignprojects/gitserver:latest

RUN repo create project
COPY test_rsa.pub /home/git/.ssh/test_rsa.pub
RUN key add $(cat /home/git/.ssh/test_rsa.pub)