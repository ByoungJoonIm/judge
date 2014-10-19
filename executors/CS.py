import os
import subprocess

from cptbox import CHROOTSecurity, SecurePopen, PIPE, ALLOW
from cptbox.syscalls import *
from error import CompileError
from .utils import test_executor
from .resource_proxy import ResourceProxy
from judgeenv import env

CS_FS = ['.*\.so', '/proc/(?:self/|xen)']


class Executor(ResourceProxy):
    def __init__(self, problem_id, source_code):
        super(Executor, self).__init__()
        source_code_file = self._file('%s.cs' % problem_id)
        self.name = '%s.exe' % problem_id
        with open(source_code_file, 'wb') as fo:
            fo.write(source_code)
        csc_args = [env['runtime']['csc'], source_code_file]
        csc_process = subprocess.Popen(csc_args, stderr=subprocess.PIPE, cwd=self._dir)
        _, compile_error = csc_process.communicate()
        if csc_process.returncode != 0:
            raise CompileError(compile_error)

    def _get_security(self):
        sec = CHROOTSecurity(CS_FS)
        sec[sys_sched_getaffinity] = ALLOW
        return sec

    def launch(self, *args, **kwargs):
        return SecurePopen(['mono', self.name] + list(args),
                           executable=env['runtime']['mono'],
                           security=self._get_security(),
                           time=kwargs.get('time'),
                           memory=kwargs.get('memory'),
                           stderr=(PIPE if kwargs.get('pipe_stderr', False) else None),
                           env={}, cwd=self._dir)

    def launch_unsafe(self, *args, **kwargs):
        return subprocess.Popen(['mono', self.name] + list(args),
                                executable=env['runtime']['mono'],
                                env={},
                                cwd=self._dir,
                                **kwargs)


def initialize():
    if 'csc' not in env['runtime'] or 'mono' not in env['runtime']:
        return False
    if not os.path.isfile(env['runtime']['csc']):
        return False
    return test_executor('CS', Executor, '''\
using System;

class test {
    public static void Main(string[] args) {
        Console.WriteLine("Hello, World!");
    }
}''')
