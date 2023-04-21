FROM ensignprojects/gitserver

RUN repo create project
COPY test_rsa.pub /home/git/.ssh/test_rsa.pub
RUN key add $(cat /home/git/.ssh/test_rsa.pub)