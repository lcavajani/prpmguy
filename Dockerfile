FROM opensuse/leap

RUN zypper ref && \
    zypper -n in python3 python3-PyYAML python3-requests osc && \
    zypper clean -a

RUN mkdir -p /app && chown 65534.65534 /app

WORKDIR /app

ADD ./prpmguy.py /app/

# uid=65534(nobody) gid=65534(nobody) groups=65534(nobody)
USER 65534

ENTRYPOINT  [ "python3", "/app/prpmguy.py" ]
