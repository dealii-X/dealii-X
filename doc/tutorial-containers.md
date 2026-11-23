# Run the dealii-X tutorial stack

From the root of the dealii-X repository, initialize the local work directory
and SSH key, pull the images, and start the stack:

```sh
./scripts/tutorial-init.sh
docker compose pull --ignore-buildable
docker compose build --pull coral-ssh-slurm
docker compose up -d
```

Open the platform through noVNC at <http://localhost:6080> and Coral Visualizer
at <http://localhost:8008>. The shared work directory on the host is
`.dealiix-tutorial/shared-data`. The platform uses examples copied from the same
ImmersX image that runs the backend, so those examples follow the selected
ImmersX tag. Stop the stack with `docker compose down`.

## Development and release tags

By default the stack uses the `main` tags of ImmersX, Platform, and Coral
Visualizer. dealii-X builds the SSH/Slurm execution service on top of the
selected published ImmersX image. ImmersX provides its applications, Coral,
and the plugins.
To select a published release combination, set each service's tag in `.env`:

```dotenv
IMMERSX_TAG=main
CORAL_VISUALIZER_TAG=main
DEALIIX_PLATFORM_TAG=main
```

Replace `main` with the published release tag for that component. The tags can
differ between services. Compose reads these tags when pulling and building the stack. Run the same
three Compose commands after updating a tag. `docker compose config` shows the
resolved service images and the ImmersX base of the execution service.
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

The dealii-X workflow builds and tests SSH and Slurm on AMD64 and ARM64 before
publishing `ghcr.io/dealii-x/dealii-x:main`. A stable Git tag on `main` promotes
the tested image for that revision, building it first when needed. The
`latest` tag follows the highest published stable version. Compose can build
the same execution Dockerfile locally to select a different ImmersX base.
