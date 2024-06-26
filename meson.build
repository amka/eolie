project('eolie', 'c',
  version: '0.9.101',
  meson_version: '>= 0.65.0',
)

revision = run_command('bin/revision.sh').stdout().strip()
if revision == ''
  revision=meson.project_version()
endif

if get_option('devel').enabled()
  appid='None'
else
  appid='org.gnome.Eolie'
endif

i18n = import('i18n')
project_id = 'org.gnome.Eolie'

message('Looking for dependencies')
pymod = import('python')
python = pymod.find_installation()

dependency('glib-2.0', version: '>= 2.70')
dependency('gio-2.0', version: '>= 2.70')
dependency('gtk4', version: '>= 4.12.0')
dependency('libadwaita-1', version: '>=1.4.0')
dependency('webkitgtk-6.0', version: '>= 2.42.0')


env = environment()

python_dir = join_paths(get_option('prefix'), python.get_install_dir())
LIBEXEC_DIR = join_paths(get_option('prefix'), get_option('libexecdir'))
EXTENSION_DIR = join_paths(get_option('prefix'), get_option('libdir'), meson.project_name())
DATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
bindir = join_paths(get_option('prefix'), get_option('bindir'))

conf = configuration_data()
conf.set('PACKAGE_URL', 'https://wiki.gnome.org/Apps/Eolie')
conf.set('DATA_DIR', DATA_DIR)
conf.set('EXTENSION_DIR', EXTENSION_DIR)
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
conf.set('PYTHON_DIR', python_dir)
conf.set('libexecdir', LIBEXEC_DIR)
conf.set('VERSION', meson.project_version())
conf.set('REVISION', revision)
conf.set('APPID', appid)

subdir('data')
subproject('po')
subdir('search-provider')

install_subdir(
  'eolie',
  install_dir: python_dir
)

message('Preparing init file')
configure_file(
  input: 'eolie.in',
  output: 'eolie',
  configuration: conf,
  install_dir: bindir
)

meson.add_install_script('meson_post_install.py')
