%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"
)}

%define proj_name simpleutil

Name:           python-%{proj_name}
Version:        1.0.0
Release:        0%{?dist}
Summary:        simpleutil copy from openstack
Group:          Development/Libraries
License:        MPLv1.1 or GPLv2
URL:            http://github.com/Lolizeppelin/%{proj_name}
Source0:        %{proj_name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires:  python-setuptools >= 11.0

Requires:       python >= 2.6.6
Requires:       python < 3.0
Requires:       python-netaddr >= 0.7.5
Requires:       python-eventlet >= 0.15.2
Requires:       python-six >= 1.9.0
Requires:       python-funcsigs >= 0.4
Requires:       python-ntplib >= 0.3.3


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
%dir %{python_sitelib}/%{name}*
%{python_sitelib}/%{name}*/*
%doc README.rst

%changelog

* Mon Aug 29 2017 Lolizeppelin <lolizeppelin@gmail.com> - 1.0.0
- Initial Package