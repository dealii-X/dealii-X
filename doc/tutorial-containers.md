# Run the dealii-X tutorial stack

From the root of the dealii-X repository, initialize the local work directory
and SSH key, pull the images, and start the stack:

```sh
./scripts/tutorial-init.sh
docker compose pull
docker compose up -d --no-build
```

Open the platform through noVNC at <http://localhost:6080> and Coral Visualizer
at <http://localhost:8008>. The shared work directory on the host is
`.dealiix-tutorial/shared-data`. The platform uses examples copied from the same
ImmersX image that runs the backend, so those examples follow the selected
ImmersX tag. Stop the stack with `docker compose down`.

## Development and release tags

The development Compose uses `main` for ImmersX, the dealii-X execution
service, Coral Visualizer, and Platform. The execution service builds from
the published ImmersX `main` image, which supplies Coral, MetricFlowX, and the
ImmersX plugins.

For a stable deployment, check out the dealii-X release tag and download
`compose.release.json` from the `dealii-x-compose-<tag>` artifact of that
tag's **Tutorial Compose** workflow. Put it in the repository root and run:

```sh
./scripts/tutorial-init.sh
docker compose -f compose.release.json pull
docker compose -f compose.release.json up -d
```

The release Compose uses the published execution image and records the
explicit dependency versions and digests selected when it was built.
Use the same `-f compose.release.json` option to stop the release stack.

For local development with a different ImmersX base, set `IMMERSX_TAG` to
the desired tag and `DEALIIX_TAG=local`, then run
`docker compose build --pull coral-ssh-slurm` followed by
`docker compose up -d`. Keep these variables set for both commands.

Configure the local ports with `CORAL_SSH_PORT`, `VISUALIZER_PORT`, or
`PLATFORM_PORT`. The defaults are 2222, 8008, and 6080, bound to loopback.

## Platform settings

If the platform image has no configured remote target, use these settings:

| Setting | Value |
| --- | --- |
| Host and port | `coral-ssh-slurm`, `22` |
| Username and SSH key | `root`, `/run/tutorial-ssh/id_ed25519` |
| Coral command | `/usr/local/bin/coral-release` |
| 2D plugin | `/opt/dealiix/immersx/Release/lib/immersx/coral/libcoral_backend_immersx_2.so` |
| Work directory | `/app/shared-data` |
| MPI launcher | `srun` |
| Visualizer URL | `http://coral-visualizer:8080` |

Run **Validate & Sync**, then open an example from
`/opt/dealiix/immersx/coral/examples`. VTK output in the shared work directory
is visible to Coral Visualizer under `/deploy/data`.

The Platform publication and end-to-end checks are tracked in
[Platform #259](https://github.com/2listic/dealiiX-platform/issues/259).
Native ARM64 Visualizer publication is tracked in
[Visualizer #47](https://github.com/2listic/coral-visualizer/issues/47).
Select image tags available for your host architecture.

## Published execution service

The dealii-X workflow tests SSH and Slurm on AMD64 and ARM64 before
publishing `ghcr.io/dealii-x/dealii-x:main`. A stable Git tag on `main`
resolves the highest stable published version of each direct dependency,
then builds and tests the execution image using that ImmersX release. Each
dependency must provide an index for both architectures. The workflow publishes
the explicit dealii-X version, and `latest` follows the highest published
stable release. The execution image labels record the dependency references so
the Compose file can also be regenerated using
`scripts/render_release_compose.sh <immersx> <visualizer> <platform> <execution>`.
