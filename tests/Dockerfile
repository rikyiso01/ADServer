FROM debian:bullseye-20230208-slim

RUN apt-get update &&\
    apt-get install -y --no-install-recommends openssh-server &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN echo "root:test" | chpasswd &&\
    sed --in-place 's/^\(PermitRootLogin\|UsePAM\)/#\1/' /etc/ssh/sshd_config &&\
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config &&\
    echo "UsePAM yes" >> sshd_config

RUN service ssh start

COPY project /root/project

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]