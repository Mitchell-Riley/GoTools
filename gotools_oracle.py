import sublime
import sublime_plugin
import os

from .gotools_util import Buffers
from .gotools_util import GoBuffers
from .gotools_util import Logger
from .gotools_util import ToolRunner
from .gotools_settings import GoToolsSettings

class GotoolsOracleCommand(sublime_plugin.TextCommand):
  def is_enabled(self):
    return GoBuffers.is_go_source(self.view)

  def run(self, edit, command=None):
    self.settings = GoToolsSettings()
    self.logger = Logger(self.settings)
    self.runner = ToolRunner(self.settings, self.logger)

    if not command:
      self.logger.log("command is required")
      return

    filename, row, col, offset, offset_end = Buffers.location_at_cursor(self.view)
    pos = filename+":#"+str(offset)

    # Build up a package scope contaning all packages the user might have
    # configured.
    # TODO: put into a utility
    package_scope = []
    for p in self.settings.build_packages:
      package_scope.append(os.path.join(self.settings.project_package, p))
    for p in self.settings.test_packages:
      package_scope.append(os.path.join(self.settings.project_package, p))
    for p in self.settings.tagged_test_packages:
      package_scope.append(os.path.join(self.settings.project_package, p))

    sublime.active_window().run_command("hide_panel", {"panel": "output.gotools_oracle"})

    possible_commands = ["callees", "callers", "callstack", "definition",
      "describe", "freevars", "implements", "peers", "referrers", "what"]
    if command not in possible_commands:
      self.logger.status("unrecognized oracle command")
      return

    if command == "freevars":
      pos = filename+":#"+str(offset)+","+"#"+str(offset_end)
    
    sublime.set_timeout_async(lambda: self.do_plain_oracle(command, pos, package_scope), 0)

  def do_plain_oracle(self, mode, pos, package_scope=[], regex="^(.*):(\d+):(\d+):(.*)$"):
    self.logger.status("running oracle "+mode+"...")
    args = ["-pos="+pos, "-format=plain", mode]
    if len(package_scope) > 0:
      args = args + package_scope
    output, err, rc = self.runner.run("oracle", args, timeout=60)
    self.logger.log("oracle "+mode+" output: " + output.rstrip())

    if rc != 0:
      self.logger.status("oracle call failed (" + str(rc) +")")
      return
    self.logger.status("oracle "+mode+" finished")

    panel = self.view.window().create_output_panel('gotools_oracle')
    panel.set_scratch(True)
    panel.settings().set("result_file_regex", regex)
    panel.run_command("select_all")
    panel.run_command("right_delete")
    panel.run_command('append', {'characters': output})
    self.view.window().run_command("show_panel", {"panel": "output.gotools_oracle"})
