%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"
)}

%define proj_name simpleutil

%define _release RELEASEVERSION

Name:           python-%{proj_name}
Version:        RPMVERSION
Release:        %{_release}%{?dist}
Summary:        simpleutil copy from openstack
Group:          Development/Libraries
License:        MPLv1.1 or GPLv2
URL:            http://github.com/Lolizeppelin/%{proj_name}
Source0:        %{proj_name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires:  python-setuptools >= 11.0
BuildRequires:  gcc >= 4.0
BuildRequires:  python-devel >= 2.6.6
BuildRequires:  python-devel < 3.0

Requires:       python >= 2.6.6
Requires:       python < 3.0
Requires:       python-netaddr >= 0.7.5
Requires:       python-eventlet >= 0.18.4
Requires:       python-six >= 1.9.0
Requires:       python-funcsigs >= 0.4
Requires:       python-ntplib >= 0.3.3
Requires:       python-dateutil >= 2.4.2
Requires:       python-argparse >= 1.2.1
Requires:       tar >= 1.2.0
Requires:       unzip >= 5.0

%if 0%{?rhel} > 6
Requires:       python-jsonschema > 2.5.0, python-jsonschema < 3.0.0
%endif
%if 0%{?rhel} < 7
Requires:       python-jsonschema >= 2.0.0, python-jsonschema < 2.5.0
Requires:       python-importlib >= 1.0
%endif

%description
utils copy from openstack


%prep
%setup -q -n %{proj_name}-%{version}
rm -rf %{proj_name}.egg-info

%build
%{__python} setup.py build

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%clean
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root,-)
%{python_sitelib}/%{proj_name}/*
%{python_sitelib}/%{proj_name}-%{version}-*.egg-info/*
%dir %{python_sitelib}/%{proj_name}-%{version}-*.egg-info/
%doc README.rst
%doc doc/*

%changelog

* Mon Aug 29 2017 Lolizeppelin <lolizeppelin@gmail.com> - 1.0.0
- Initial Package