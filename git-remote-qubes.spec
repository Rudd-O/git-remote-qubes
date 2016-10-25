%define debug_package %{nil}

%define mybuildnumber %{?build_number}%{?!build_number:1}

Name:           git-remote-qubes
Version:        0.0.1
Release:        %{mybuildnumber}%{?dist}
Summary:        Inter-VM git push and pull
BuildArch:      noarch

License:        GPLv3+
URL:            https://github.com/Rudd-O/git-remote-qubes
Source0:        https://github.com/Rudd-O/%{name}/archive/{%version}.tar.gz#/%{name}-%{version}.tar.gz

BuildRequires:  make
BuildRequires:  sed
BuildRequires:  python2

Requires:       python2

%description
This package lets you setup Git servers on your Qubes OS VMs.

%prep
%setup -q

%build
# variables must be kept in sync with install
make DESTDIR=$RPM_BUILD_ROOT BINDIR=%{_bindir} SYSCONFDIR=%{_sysconfdir} SITELIBDIR=%{python_sitelib}

%install
rm -rf $RPM_BUILD_ROOT
# variables must be kept in sync with build
make install-vm DESTDIR=$RPM_BUILD_ROOT BINDIR=%{_bindir} SYSCONFDIR=%{_sysconfdir} SITELIBDIR=%{python_sitelib}

%check
if grep -r '@.*@' $RPM_BUILD_ROOT ; then
    echo "Check failed: files with AT identifiers appeared" >&2
    exit 1
fi

%files
%attr(0755, root, root) %{_bindir}/git-*-qubes
%attr(0644, root, root) %{python_sitelib}/gitremotequbes/*.py
%attr(0644, root, root) %{python_sitelib}/gitremotequbes/*.pyc
%attr(0644, root, root) %{python_sitelib}/gitremotequbes/*.pyo
%attr(0755, root, root) %{_sysconfdir}/qubes-rpc/ruddo.Git
%doc README.md

%changelog
* Mon Oct 24 2016 Manuel Amador (Rudd-O) <rudd-o@rudd-o.com>
- Initial release.
