Name:           bbswitch-gui
Version:        0.1.0
Release:        1%{?dist}
Summary:        GUI for monitoring and toggling NVIDIA GPU power on Optimus laptops

License:        GPLv3+
URL:            https://github.com/polter-rnd/bbswitch-gui
Source0:        https://github.com/polter-rnd/bbswitch-gui/archive/%{version}/bbswitch-gui-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  python3-py3nvml

Requires:       gtk3
Requires:       psmisc
Requires:       bbswitchd
Requires:       python3-gobject
Requires:       python3-py3nvml

%?python_enable_dependency_generator


%description
Provides a user-friendly interface for managing power state
and monitoring utilization of dedicated graphics adapter.

Useful for pre-Turing GPU generations without dynamic power management features,
allows to fully benefit from NVIDIA PRIME Render Offload technology
without need to keep graphics adapter turned on all the time.


%prep
%autosetup -p1 -n bbswitch-gui-%{version}


%build
%meson
%meson_build


%install
%meson_install


%files
%license LICENSE
%{_bindir}/bbswitch-gui
%{python3_sitelib}/bbswitch_gui/*
%{_datadir}/applications/bbswitch-gui.desktop
%{_datadir}/icons/hicolor/scalable/status/*-symbolic.svg
%{_datadir}/icons/hicolor/scalable/apps/bbswitch-gui.svg


%changelog
* Wed Jan 18 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.0-1
- Initial release
