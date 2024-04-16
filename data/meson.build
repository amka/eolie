gnome = import('gnome')

message('Compiling blueprints')

blueprints = custom_target('blueprints',
  input: files(
    'ui/about_dialog.blp',
    'ui/bookmark_edit.blp',
    'ui/bookmark_rating_widget.blp',
    'ui/dialog_clear_data.blp',
    'ui/dialog_credentials.blp',
    'ui/dialog_import_bookmarks.blp',
    'ui/dialog_modify_ua.blp',
    'ui/dialog_notifications.blp',
    'ui/dialog_search_engine.blp',
    'ui/languages_menu.blp',
    'ui/popover_credentials.blp',
    'ui/popover_downloads.blp',
    'ui/popover_geolocation.blp',
    'ui/popover_java_script.blp',
    'ui/popover_images.blp',
    'ui/popover_web_view.blp',
    'ui/popover_uri.blp',
    'ui/quit_dialog.blp',
    'ui/row_download.blp',
    'ui/scripts_menu.blp',
    'ui/settings_dialog.blp',
    'ui/shortcuts.blp',
    'ui/sites_manager_child.blp',
    'ui/toolbar_actions.blp',
    'ui/toolbar_end.blp',
    'ui/toolbar_menu.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

message('Compiling resources')

gnome.compile_resources(
  meson.project_name(),
  meson.project_name() + '.gresource.xml',
  gresource_bundle: true,
  dependencies: blueprints,
  source_dir: '.',
  install_dir: DATA_DIR,
  install: true
)

# Installing the schema file 
install_data(
  project_id + '.gschema.xml',
  install_dir: 'share/glib-2.0/schemas'
)

# Not available in GNOME Platform
if get_option('flatpak').enabled()
  install_data(
    'org.gnome.settings-daemon.plugins.color.gschema.xml',
    install_dir: 'share/glib-2.0/schemas'
  )
endif

# Merging the translations with the desktop file
i18n.merge_file(
  output: project_id + '.desktop',
  input: project_id + '.desktop.in',
  po_dir: join_paths(meson.source_root(), 'po'),
  type: 'desktop',
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'applications')
)

# Validating the desktop file
desktop_file_validate = find_program('desktop-file-validate', required:false)
if desktop_file_validate.found()
  test (
    'Validate desktop file',
    desktop_file_validate,
    args: join_paths(meson.current_build_dir (), project_id + '.desktop')
  )
endif

# Merging the translations with the appdata file
i18n.merge_file(
  output: project_id + '.appdata.xml',
  input: project_id + '.appdata.xml.in',
  po_dir: join_paths(meson.source_root(), 'po'),
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'metainfo')
)

# Validating the appdata file
appstreamcli = find_program('appstream-util', required: false)
if appstreamcli.found()
  test (
    'Validate appdata file',
    appstreamcli,
    args: ['validate-relax', join_paths(meson.current_build_dir (), project_id + '.appdata.xml')]
  )
endif

# Validating schemas
compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

message('Making a list of icons')
subdir('icons')
