Name:           bbswitch-gui
Version:        0.1.5
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

Requires:       bbswitchd
Requires:       gtk3
Requires:       libappindicator-gtk3
Requires:       python3-gobject
Requires:       python3-py3nvml
Requires:       psmisc
Requires:       hwdata


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
%{_datadir}/applications/io.github.polter-rnd.bbswitch-gui.desktop
%{_datadir}/icons/hicolor/scalable/status/*-symbolic.svg
%{_datadir}/icons/hicolor/scalable/apps/bbswitch-gui.svg


%changelog
* Sat Mar 18 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.5-1
- Hotfix: added missing icon

* Sat Mar 18 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.4-1
- Update UI, refine icons
- Fix detecting module load error

* Tue Mar 14 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.3-1
- Minor fixes, stability enhancements

* Sun Mar 12 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.2-2
- Remove unused %python_enable_dependency_generator macro

* Sat Mar 11 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.2-1
- Add warning about incompatibility with nouveau driver
- Fix false positive "Loading kernel modules" message

* Thu Jan 26 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.1-1
- Increase default window size
- Fix compatibility with legacy pynvml attributes
- Toggle GPU on button release instead of press

* Wed Jan 18 2023 Pavel Artsishevsky <polter.rnd@gmail.com> - 0.1.0-1
- Initial release
