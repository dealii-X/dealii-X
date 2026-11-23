# syntax=docker/dockerfile:1
ARG IMMERSX_IMAGE=ghcr.io/luca-heltai/immersx:main
FROM ${IMMERSX_IMAGE}
USER root

RUN apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        munge slurmd slurm-client slurmctld slurmdbd mariadb-server openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/ssh/ssh_host_* /etc/munge/munge.key
RUN mkdir -p /run/sshd /root/.ssh /var/log/slurm /var/spool/slurmctld \
    /var/spool/slurmd.slurmnode1 /app/shared-data \
    && printf '%s\n' 'PermitRootLogin prohibit-password' 'PasswordAuthentication no' \
       > /etc/ssh/sshd_config.d/00-dealiix.conf

COPY slurm.conf slurmdbd.conf cgroup.conf /etc/slurm/
COPY --chmod=755 entrypoint.sh /usr/local/bin/dealiix-execution
RUN chmod 600 /etc/slurm/slurmdbd.conf \
    && test -x /usr/local/bin/coral-release \
    && test -f /opt/immersx/lib/immersx/coral/libcoral_backend_immersx_2.so \
    && mkdir -p /opt/dealiix/immersx \
    && ln -s /opt/immersx /opt/dealiix/immersx/Release \
    && ln -s /opt/immersx-debug /opt/dealiix/immersx/Debug

ENV OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
WORKDIR /app/shared-data
EXPOSE 22 6817 6818
ENTRYPOINT ["/usr/local/bin/dealiix-execution"]
CMD []
