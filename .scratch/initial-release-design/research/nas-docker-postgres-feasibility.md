# NAS Docker/PostgreSQL feasibility

Investigated 2026-10-18. Scope: primary-source documentation and read-only host
observations supplied by the parent investigator. No SSH connections, installation,
image pulls, container starts, database connections, or target writes by this
research task.

## Conclusion

**A dedicated PostgreSQL container on this DXP2800's SSD is a supported and
technically plausible deployment route, but it is not installed or tested.**
UGREEN explicitly lists DXP2800 among Docker-capable models. Its support material
documents a Docker application and Compose-based Projects. This establishes the
vendor route; it does not certify this specific database deployment, its performance,
or storage durability. [UGREEN model support](https://ai.ugreen.com/pages/solution-software),
[Projects](https://support.ugnas.com/detail/article/en-US/411).

The user's deployment constraint is Docker containers for the project application,
worker, and database; native project services require a separately justified,
exceptionally simple case. The container runtime itself remains host infrastructure.

## Host evidence supplied by the parent

The live read-only check reports x86_64, Debian 12 base, 8 GB-class RAM, kernel
6.18, cgroup v2 controllers, and overlay filesystem support. `/volume3` is local
ext4 on the NVMe SSD, with roughly 443 GB available; `/volume3/workspace` reports
writable to the SSH account. That is a permission query, not a successful write
or initialization test. See [host inventory](host-storage-wake-inventory.md).

Docker, dockerd, containerd, and Podman were not found on the inspected PATH;
no matching active runtime unit or socket was observed. App-manager files and
Docker-related icons exist, but neither establishes an installed engine.
Vendor PostgreSQL listens at `127.0.0.1:5432`; leave its data and service untouched.

## Supported installation route and prerequisites

1. An administrator opens UGOS Pro **App Center**, finds **Docker**, and installs
   and enables it. UGREEN documents this application-management route and requires
   Docker to be operational before dependent container applications work.
   [App Center](https://support.ugnas.com/detail/article/en-US/116),
   [container prerequisites](https://support.ugnas.com/detail/article/en-US/539).
2. Verify the actual Docker app/package available on this NAS, resulting engine
   version, administrative access, and storage location. Documentation cannot
   establish its live App Center catalogue, account permissions, or install success.
3. Deploy a manually managed **Docker Project**, importing reviewed Compose YAML.
   This route supports custom ports and mounts, unlike restricted App Center
   application packages. UGREEN's Project interface downloads images and starts
   services; invoking Deploy is a target change requiring separate authorization.
   [manual versus packaged applications](https://support.ugnas.com/detail/article/en-US/539),
   [Compose project deployment](https://support.ugnas.com/detail/article/en-US/411).

No Debian `apt install` or vendor-database reuse is necessary to follow this route.
Do not independently install a second engine alongside a vendor-managed engine.

## Dedicated database requirements

The official PostgreSQL image supports amd64. Choose an explicit supported major
and image reference at implementation. PostgreSQL 18+ mounts persistent storage at
`/var/lib/postgresql` with versioned PGDATA; 17 and earlier default to
`/var/lib/postgresql/data`. Match the selected image rather than copying an old
volume example. Initialization needs an empty directory and proper ownership;
initialization settings do not modify an existing cluster. Use a protected secret
file for the bootstrap password and a distinct non-superuser application role;
do not use host `trust` authentication. [official image](https://hub.docker.com/_/postgres).

Bind a new, user-approved SSD subdirectory on **the NAS host**. Docker bind paths
refer to its daemon host; they are writable by default, so expose only the project
directory. Do not substitute the mini-PC's NFS mount or a vendor database directory.
[bind mounts](https://docs.docker.com/engine/storage/bind-mounts/).

Use bridge networking and an explicitly selected host IP/unused port, with access
restricted to the mini-PC application. Avoid host networking and the existing
vendor listener. Docker publishes unspecified addresses broadly; a bridge network
on one host is not a cross-host private network.
[port publishing](https://docs.docker.com/engine/network/port-publishing/).

## Durability and outstanding proof

The supplied SSD mount observation includes `nobarrier`. Kernel documentation says
this disables journal write barriers, which enforce commit ordering with volatile
write caches. Power-loss protection and the full flush path therefore need
verification before promising durable acceptance. This caveat does not make
container execution infeasible; do not change mount options during investigation.
[ext4 barrier semantics](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html).

An HDD copy must be consistent: stop PostgreSQL cleanly before copying its whole
data directory, or use a supported database backup method. A live ordinary file
copy is not a valid database backup.
[PostgreSQL filesystem backup](https://www.postgresql.org/docs/current/backup-file.html).

Still untested: package installation, image retrieval, directory initialization,
container persistence across recreation/reboot, mini-PC connectivity, resource
headroom, backup restoration, performance, and power-loss durability.
