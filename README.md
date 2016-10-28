# Inter-VM Git for Qubes OS

This is a very simple Git protocol bridge between Qubes OS VMs.  With it,
you can `git pull` and `git push` between VMs without having to grant
any of the VMs any special policy privileges other than access to Git.

The advantages of this solution over Git-over-SSH or other networking
protocols are clear:

1. Better security: you do not need to network the VM that stores your
   Git repos, or take care of firewall rules.
2. More resource efficiency: you do not need to run any network-facing
   daemons, effectively saving RAM for other uses.

## Using the software

These instructions assume you have installed the software.  See the
*Installing the software* heading below for more information.

### Creating a repository

We'll assume for illustration purposes that you want to access a repository
stored in `/home/user/xyz` on your VM `servervm`.

Run the following commands on `servervm`:

```
cd /home/user
mkdir -p xyz
cd xyz
git --bare init
```

That's it.  Your new and empty repository is ready to use.

### Adding a remote to a local repository

For illustration purposes, you'll be pushing and pulling `servervm`'s `xyz`
repo on your vm `clientvm`.  Run the following commands on `clientvm`:

```
cd /home/user
git clone qubes://clientvm/home/user/xyz
```

You will get a permission dialog from dom0 asking for `ruddo.Git` access.
Accept it.  Note that accepting the permission dialog implicitly gives
Git access to all Git repos stored in `servervm`, but only for that one
execution (unless you say *Yes to all*, in which case the permission
is remembered within the policy file that you installed earlier with the
`dom0` package).

This should have cloned `xyz` from `servervm` into your `/home/user/xyz`
directory in `clientvm`.

From this point on, you can push and pull in `clientvm` from
`servervm:/home/user/xyz` to your heart's content.

If, instead of cloning, you have an existing repo, you can add a new remote
just as easily:

```
cd /home/user/existingxyz
git remote add qubesremotevm qubes://servervm/home/user/xyz
```

That addition will enable to push and pull from the remote `qubesremotevm`
which represents the repo `/home/user/xyz` in the remote VM `servervm`.

## Installing the software

There are two components for this software:

* Component 1 is the VM side of things, which implements the Git protocol
  across VMs.
* Component 2 is the dom0 side of things, which is a simple text file declaring
  the initial Git access policy for your VMs.

First, build the software,  After cloning this repository on a suitable VM,
run the command:

```
make rpm
```

This will generate two installable packages on the local directory:

* `git-remote-qubes-<version>.noarch.rpm`, which contains the Git
  protocol implementation.
* `git-remote-qubes-dom0-<version>.noarch.rpm`, which contains the
  default policy.

Copy the `git-remote-qubes-<version>.noarch.rpm` file to the template VM
or standalone VM where you plan to pull or push to / from a Git repo
stored in another Qubes VM.  Install the RPM with
`dnf install <name of the RPM>`.  At this point, this VM, as well as
any VMs using this as a template, have gained the ability to push and pull
from Git repos stored in other VMs, as well as the ability to listen on
push / pull requests from different VMs in the same system.

Now copy the `git-remote-qubes-dom0-<version>.noarch.rpm` file to
your dom0.  At this point, the default policy (`deny`) is active on
your Qubes OS system, and you can begin pushing and pulling.

Those clever among you will have discovered that there is a `Makefile`
included, and that you can use the `Makefile` to install the software on
other non-RPM templates.  I welcome pull requests to add support for
other distro packages and Qubes OS templates.

## Troubleshooting and debugging

If you are experiencing problems communicating with a Git repo in a VM,
export the variable `QUBES_DEBUG` on the side of your client (where your
local Git repo is), and look at the debugging output that appears.

As always, you can file new issues on the repo of this project for help
with fixing bugs that the programs may have.  Pull requests also welcome.
