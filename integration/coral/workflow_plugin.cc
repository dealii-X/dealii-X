#include <coral.h>
#include <coral_log.h>
#include <coral_plugin.h>

#include <cerrno>
#include <cstdlib>
#include <spawn.h>
#include <stdexcept>
#include <string>
#include <sys/wait.h>

extern char **environ;

namespace
{
  std::string invoke(const std::string &operation, const std::string &request)
  {
    // This plugin orchestrates subprocesses. It must not itself be replicated
    // across MPI ranks: the application request owns the solver's MPI launch.
    for (const auto key : {"OMPI_COMM_WORLD_RANK", "PMI_RANK", "PMIX_RANK", "SLURM_PROCID"})
      if (std::getenv(key))
        throw std::runtime_error("Workflow plugins must run serially; configure MPI in the solver request");
    const char *python = std::getenv("DEALIIX_PYTHON");
    if (!python) python = "python3";
    const char *arguments[] = {python, "-m", "dealiix.application", DEALIIX_COMPONENT,
                              operation.c_str(), request.c_str(), nullptr};
    pid_t pid;
    const int result = posix_spawnp(&pid, python, nullptr, nullptr,
                                   const_cast<char **>(arguments), environ);
    if (result != 0) throw std::runtime_error("Cannot start workflow adapter");
    int status = 0;
    while (waitpid(pid, &status, 0) < 0)
      if (errno != EINTR) throw std::runtime_error("Cannot wait for workflow adapter");
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
      throw std::runtime_error("Workflow adapter failed; inspect the stage log");
    return request;
  }
  std::string prepare(std::string request) { return invoke("prepare", request); }
  std::string validate(std::string request) { return invoke("validate", request); }
  std::string run(std::string request) { return invoke("run", request); }
  std::string export_results(std::string request) { return invoke("export", request); }
  std::string diagnostics(std::string request) { return invoke("diagnostics", request); }
}

CORAL_PLUGIN_EXPORT const char *coral_plugin_name() { return "dealiix_" DEALIIX_COMPONENT; }
CORAL_PLUGIN_EXPORT int coral_load_plugin(const char *, const CoralLogger *logger)
{
  coral_active_logger = logger;
  coral_active_plugin_name = coral_plugin_name();
  coral::detail::set_type_alias<std::string>("std::string");
  coral::NodeObject::register_elementary_type<std::string>();
  const std::string prefix = "dealiix::" DEALIIX_COMPONENT "::";
  coral::NodeObject::register_function(prepare, {prefix + "prepare", "result", "request"});
  coral::NodeObject::register_function(validate, {prefix + "validate", "result", "request"});
  coral::NodeObject::register_function(run, {prefix + "run", "result", "request"});
  coral::NodeObject::register_function(export_results, {prefix + "export", "result", "request"});
  coral::NodeObject::register_function(diagnostics, {prefix + "diagnostics", "result", "request"});
  return 0;
}
CORAL_PLUGIN_EXPORT void coral_unload_plugin() {}
