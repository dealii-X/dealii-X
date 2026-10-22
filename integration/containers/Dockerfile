# syntax=docker/dockerfile:1.7
ARG PYTHON_BASE=python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
ARG DEALII_BASE=dealii/dealii:v9.7.1-noble@sha256:28a40c95e76879c717a96ea3f5c87cc00ec1d7a4ce9d250ab936fb723eab6995
ARG FOURC_BASE=ghcr.io/4c-multiphysics/4c-dependencies-ubuntu24.04:main@sha256:290a0a72254b607bf0ffea9b2845fd03782b62e5a6b587423045eb4bb322d7eb
ARG NODE_BASE=node:22-bookworm@sha256:0e5f906573693feaa1e21057ebdcfdb5bd5021f050b2dc7c9deceb629c7da2a8

FROM ${PYTHON_BASE} AS contracts
COPY integration /opt/dealiix-integration
ENV PYTHONPATH=/opt/dealiix-integration
WORKDIR /work
RUN python3 -m unittest discover -s /opt/dealiix-integration/tests -v
ENTRYPOINT ["python3", "-m", "dealiix"]
CMD ["--help"]

# Supply --build-context sources=<isolated snapshots directory>. Source SHAs
# and every applied patch are verified by the build driver.
FROM ${DEALII_BASE} AS toolchain
USER root
ARG JOBS=4
COPY integration /opt/dealiix-integration
COPY --from=sources / /sources/
ENV PYTHONPATH=/opt/dealiix-integration
RUN python3 -m dealiix.build dealii --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS}
RUN python3 -m dealiix.build coral --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} \
    --dealii-dir /opt/dealiix/dealii/lib/cmake/deal.II
RUN cmake -S /opt/dealiix-integration/coral -B /build/plugins \
    -DCMAKE_PREFIX_PATH=/opt/dealiix/coral -DCMAKE_INSTALL_PREFIX=/opt/dealiix \
    && cmake --build /build/plugins --parallel ${JOBS} && cmake --install /build/plugins
ENV DEAL_II_DIR=/opt/dealiix/dealii/lib/cmake/deal.II
ENV coral_DIR=/opt/dealiix/coral/lib/cmake/coral

FROM toolchain AS metric-flow-x
RUN python3 -m dealiix.build metric-flow-x --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} \
    --dealii-dir ${DEAL_II_DIR} --target blood_flow

FROM toolchain AS immersx
RUN python3 -m dealiix.build immersx --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} \
    --dealii-dir ${DEAL_II_DIR} --coral-dir ${coral_DIR}

FROM toolchain AS lifex
RUN python3 -m dealiix.build lifex --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} --dealii-dir ${DEAL_II_DIR}

FROM toolchain AS exabrain
RUN python3 -m dealiix.build exabrain --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} --dealii-dir ${DEAL_II_DIR}

FROM toolchain AS exadg
RUN python3 -m dealiix.build exadg --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} --dealii-dir ${DEAL_II_DIR}

FROM toolchain AS polydeal
RUN python3 -m dealiix.build polydeal --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS} --dealii-dir ${DEAL_II_DIR}

FROM toolchain AS psctoolkit
RUN python3 -m dealiix.build psctoolkit --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS}

FROM ${FOURC_BASE} AS four-c
USER root
ARG JOBS=4
COPY integration /opt/dealiix-integration
COPY --from=sources /4c /sources/4c
ENV PYTHONPATH=/opt/dealiix-integration
RUN python3 -m dealiix.build 4c --manifest /opt/dealiix-integration/sources.json \
    --source-root /sources --build-root /build --prefix-root /opt/dealiix --jobs ${JOBS}
RUN python3 /opt/dealiix-integration/containers/collect-runtime.py /opt/dealiix/4c /opt/fourc-runtime

FROM ${NODE_BASE} AS platform
COPY integration /opt/dealiix-integration
COPY --from=sources /platform /sources/platform
WORKDIR /sources/platform
# Apply the reviewed integration patch before npm's lockfile-based install.
RUN git apply /opt/dealiix-integration/patches/platform.patch \
    && npm ci --ignore-scripts && npm run check:electron && npm run check \
    && npm test && npm run build

FROM ${DEALII_BASE} AS complete
USER root
COPY integration /opt/dealiix-integration
COPY --from=toolchain /opt/dealiix /opt/dealiix
COPY --from=metric-flow-x /opt/dealiix/metric-flow-x /opt/dealiix/metric-flow-x
COPY --from=immersx /opt/dealiix/immersx /opt/dealiix/immersx
COPY --from=lifex /opt/dealiix/lifex /opt/dealiix/lifex
COPY --from=exabrain /opt/dealiix/exabrain /opt/dealiix/exabrain
COPY --from=exadg /opt/dealiix/exadg /opt/dealiix/exadg
COPY --from=polydeal /opt/dealiix/polydeal /opt/dealiix/polydeal
COPY --from=psctoolkit /opt/dealiix/psctoolkit /opt/dealiix/psctoolkit
COPY --from=four-c /opt/dealiix/4c /opt/dealiix/4c
COPY --from=four-c /opt/fourc-runtime /opt/fourc-runtime
COPY --from=platform /sources/platform/dist /opt/dealiix/platform/dist
COPY --from=platform /sources/platform/dist-electron /opt/dealiix/platform/dist-electron
ENV PYTHONPATH=/opt/dealiix-integration
ENV PATH=/opt/dealiix/coral/bin/Release:/opt/dealiix/metric-flow-x/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LD_LIBRARY_PATH=/opt/dealiix/lib/dealiix:/opt/dealiix/coral/lib/Release:/opt/dealiix/dealii/lib
WORKDIR /work
CMD ["bash"]
