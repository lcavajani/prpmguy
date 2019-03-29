FROM opensuse/leap

RUN zypper ref && \
    zypper -n in python3 python3-PyYAML python3-requests osc && \
    zypper clean -a

ADD SUSE_Trust_Root.crt.pem /etc/pki/trust/anchors/

RUN update-ca-certificates

RUN mkdir -p /app

WORKDIR /app

ADD ../prpmguy.py /app/

RUN chown -Rf 65534.65534 /app

ADD ./entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

# uid=65534(nobody) gid=65534(nobody) groups=65534(nobody)
USER 65534:65534

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
