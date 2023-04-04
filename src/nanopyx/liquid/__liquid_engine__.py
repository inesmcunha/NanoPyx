import os
import time
import difflib
from pathlib import Path
import inspect
import random

import numpy as np
import yaml

from .. import __config_folder__
from .__njit__ import njit_works
from .__opencl__ import opencl_works, cl_dp


class LiquidEngine:
    """
    Base class for parts of the NanoPyx Liquid Engine
    """

    RUN_TYPE_OPENCL: int = 0
    RUN_TYPE_UNTHREADED: int = 1
    RUN_TYPE_THREADED: int = 2
    RUN_TYPE_THREADED_STATIC: int = 3
    RUN_TYPE_THREADED_DYNAMIC: int = 4
    RUN_TYPE_THREADED_GUIDED: int = 5
    RUN_TYPE_PYTHON: int = 6
    RUN_TYPE_NJIT: int = 7

    # designations are stored in the config files, to associate runtime statistics
    RUN_TYPE_DESIGNATION = {
        RUN_TYPE_OPENCL: "OpenCL",
        RUN_TYPE_UNTHREADED: "Unthreaded",
        RUN_TYPE_THREADED: "Threaded",
        RUN_TYPE_THREADED_STATIC: "Threaded_static",
        RUN_TYPE_THREADED_DYNAMIC: "Threaded_dynamic",
        RUN_TYPE_THREADED_GUIDED: "Threaded_guided",
        RUN_TYPE_PYTHON: "Python",
        RUN_TYPE_NJIT: "Numba",
    }

    _has_opencl: bool = False
    _has_unthreaded: bool = False
    _has_threaded: bool = False
    _has_threaded_static: bool = False
    _has_threaded_dynamic: bool = False
    _has_threaded_guided: bool = False
    _has_python: bool = False
    _has_njit: bool = False

    _random_testing: bool = True
    _show_info: bool = False  # print what's going on

    _default_fastest: int = RUN_TYPE_OPENCL
    _last_run_type: int = None
    _last_run_time: float = None

    def __init__(self, clear_config=False):
        """
        Initialize the Liquid Engine
        :param clear_config: whether to clear the config file
        """
        # Check if OpenCL is available
        if not opencl_works():
            self._has_opencl = False
            if self._default_fastest == self.RUN_TYPE_OPENCL:
                self._default_fastest = self.RUN_TYPE_THREADED

        # Check if Numba is available
        if not njit_works():
            self._has_njit = False

        # Load the config file
        # e.g.: ~/.nanopyx/liquid/_le_interpolation_nearest_neighbor.cpython-310-darwin/ShiftAndMagnify.yml
        base_path = os.path.join(
            __config_folder__,
            "liquid",
            os.path.split(
                os.path.splitext(inspect.getfile(self.__class__))[0]
            )[1],
        )
        os.makedirs(base_path, exist_ok=True)

        self._config_file = os.path.join(
            base_path, self.__class__.__name__ + ".yml"
        )

        if not clear_config and os.path.exists(self._config_file):
            with open(self._config_file) as f:
                self._cfg = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self._cfg = {}

        # Initialize missing dictionaries in cfg
        for run_type_designation in self.RUN_TYPE_DESIGNATION.values():
            if run_type_designation not in self._cfg:
                self._cfg[run_type_designation] = {}

    def is_opencl_enabled(self):
        """
        Returns whether OpenCL is enabled
        :return: whether OpenCL is enabled
        :rtype: bool
        """
        return self._has_opencl

    def is_njit_enabled(self):
        """
        Returns whether Numba is enabled
        :return: whether Numba is enabled
        :rtype: bool
        """
        return self._has_njit

    def set_opencl_enabled(self, enabled: bool = True):
        """
        Sets whether OpenCL is enabled
        :param enabled: whether OpenCL is enabled
        """
        self._has_opencl = enabled

    def set_opencl_disabled_if_no_double_support(self):
        """
        Sets whether OpenCL is enabled
        :param enabled: whether OpenCL is enabled
        """
        if not cl_dp:
            self._has_opencl = False

    def set_njit_enabled(self, enabled: bool = True):
        """
        Sets whether Numba is enabled
        :param enabled: whether Numba is enabled
        """
        self._has_njit = enabled

    def run(self, *args, **kwds):
        """
        Runs the function with the given args and kwargs
        Should be overridden by the any class that inherits from this class
        """
        return self._run(*args, **kwds)

    def benchmark(self, *args, **kwargs):
        """
        Benchmark the different run types
        :param args: args for the run method
        :param kwargs: kwargs for the run method
        :return:  a list of tuples containing the run time, run type name and return value
        :rtype: [[run_time, run_type_name, return_value], ...]
        """
        # Create some lists to store runtimes and return values of run types
        run_times = {}
        returns = {}
        run_types = []

        if self._has_opencl:
            run_types.append(self.RUN_TYPE_OPENCL)
        if self._has_threaded:
            run_types.append(self.RUN_TYPE_THREADED)
        if self._has_threaded_static:
            run_types.append(self.RUN_TYPE_THREADED_STATIC)
        if self._has_threaded_dynamic:
            run_types.append(self.RUN_TYPE_THREADED_DYNAMIC)
        if self._has_threaded_guided:
            run_types.append(self.RUN_TYPE_THREADED_GUIDED)
        if self._has_unthreaded:
            run_types.append(self.RUN_TYPE_UNTHREADED)
        if self._has_python:
            run_types.append(self.RUN_TYPE_PYTHON)
        if self._has_njit:
            run_types.append(self.RUN_TYPE_NJIT)
            # Trigger compilation
            try:
                self._run_njit()
            except TypeError:
                print(
                    "Consider adding default arguments to njit implementation to trigger early compilation"
                )

        for run_type in run_types:
            designation = self.RUN_TYPE_DESIGNATION[run_type]
            r = self._run(*args, run_type=run_type, **kwargs)
            run_times[run_type] = self._last_run_time
            returns[run_type] = r
            mean, std, n = self.get_mean_std_run_time(
                run_type, *args, **kwargs
            )
            self._print(
                f"{designation} run time: {format_time(self._last_run_time)}; "
                + f"mean: {format_time(mean)}; std: {format_time(std)}; runs: {n}"
            )

        # Sort run_times by value
        speed_sort = []
        for run_type in sorted(run_times, key=run_times.get, reverse=False):
            speed_sort.append(
                (
                    run_times[run_type],
                    self.RUN_TYPE_DESIGNATION[run_type],
                    returns[run_type],
                )
            )

        print(f"Fastest run type: {speed_sort[0][1]}")
        print(f"Slowest run type: {speed_sort[-1][1]}")

        # Compare each run type against each other, sorted by speed
        for i in range(len(speed_sort)):
            if i not in run_times or run_times[i] is None:
                continue
            for j in range(i + 1, len(speed_sort)):
                if j not in run_times or run_times[j] is None:
                    continue

                print(
                    f"{speed_sort[i][1]} is {speed_sort[j][0]/speed_sort[i][0]:.2f} faster than {speed_sort[j][1]}"
                )

        self._print(f"Run-times log: {self.get_run_times_log()}")
        print(
            f"Recorded fastest: {self.RUN_TYPE_DESIGNATION[self._get_fastest_run_type(*args, **kwargs)]}"
        )

        return speed_sort

    def get_mean_std_run_time(self, run_type: int, *args, **kwargs):
        """
        Get the mean and standard deviation of the run time for the given run type
        :param run_type: the run type
        :param args: args for the run method
        :param kwargs: kwargs for the run method
        :return: the mean, standard deviation of the run time and the number of runs
        """
        call_args = self._get_args_repr(*args, **kwargs)
        run_type_designation = self.RUN_TYPE_DESIGNATION[run_type]
        r = self._cfg[run_type_designation]
        if call_args not in r:
            return None, None, None

        c = r[call_args]
        sum = c[0]
        sum_sq = c[1]
        n = c[2]
        mean = sum / n
        if (n - 1) > 0:
            std = np.sqrt((sum_sq - n * mean**2) / (n - 1))
        else:
            std = 0
        return mean, std, n

    def get_run_times_log(self):
        """
        Get the run times log
        :return: the run times log
        """
        return self._cfg

    def set_show_info(self, show_info: bool):
        """
        Set whether to show info
        :param show_info: whether to show info
        :return: None
        """
        self._show_info = show_info

    def _store_run_time(self, run_type, delta, *args, **kwargs):
        """
        Store the run time in the config file
        :param run_type: the type of run
        :param delta: the time it took to run
        :param args: args for the run method
        :param kwargs: kwargs for the run method
        :return: None
        """
        self._last_run_time = delta
        call_args = self._get_args_repr(*args, **kwargs)
        run_type_designation = self.RUN_TYPE_DESIGNATION[run_type]

        r = self._cfg[run_type_designation]
        if call_args not in r:
            r[call_args] = [0, 0, 0]

        c = r[call_args]
        # add the time it took to run, later used for average
        c[0] = c[0] + delta
        # add the time it took to run squared, later used for standard deviation
        c[1] = c[1] + delta * delta
        # increment the number of times it was run
        c[2] += 1

        self._print(
            f"Storing run time: {delta} (m={c[0]/c[2]:.2f},n={c[2]})",
            call_args,
            run_type_designation,
        )

        with open(self._config_file, "w") as f:
            yaml.dump(self._cfg, f)

    def _get_fastest_run_type(self, *args, **kwargs):
        """
        Retrieves the fastest run type for the given args and kwargs
        """

        fastest = self._default_fastest
        speed_and_type = []

        call_args = self._get_args_repr(*args, **kwargs)
        # print(call_args)

        for run_type in self.RUN_TYPE_DESIGNATION:
            run_type_designation = self.RUN_TYPE_DESIGNATION[run_type]

            if run_type_designation not in self._cfg:
                self._cfg[run_type_designation] = {}
                continue

            if (
                call_args not in self._cfg[run_type_designation]
                and len(self._cfg[run_type_designation]) > 0
            ):
                # find the most similar call_args by score
                score_current = self._get_args_score(call_args)
                delta_best = 1e99
                similar_call_args: str = None
                for _call_args in self._cfg[run_type_designation]:
                    score = self._get_args_score(_call_args)
                    delta = abs(score - score_current)
                    if delta < delta_best:
                        delta_best = delta
                        similar_call_args = _call_args
                if similar_call_args is not None:
                    call_args = similar_call_args
                else:
                    # find the most similar call_args by string similarity
                    similar_args = difflib.get_close_matches(
                        call_args, self._cfg[run_type_designation].keys()
                    )
                    if len(similar_args) > 0:
                        call_args = similar_args[0]

            if call_args in self._cfg[run_type_designation]:
                run_info = self._cfg[run_type_designation][call_args]
                runtime_sum = run_info[0]
                runtime_count = run_info[2]
                speed = runtime_count / runtime_sum
                speed_and_type.append((speed, run_type))
                self._print(
                    f"{run_type_designation} run time: {speed:.2f} runs/s"
                )

        if len(speed_and_type) == 0:
            return fastest

        elif self._random_testing:
            # randomly choose a run type based on a squared speed weight
            run_type = [x[1] for x in speed_and_type]
            weights = [x[0] ** 2 for x in speed_and_type]
            return random.choices(run_type, weights=weights, k=1)[0]

        else:
            # just return the fastest
            return sorted(speed_and_type, key=lambda x: x[0], reverse=True)[0][
                1
            ]

    def _get_cl_code(self, file_name):
        """
        Retrieves the OpenCL code from the corresponding .cl file
        """
        cl_file = os.path.splitext(file_name)[0] + ".cl"
        if not os.path.exists(cl_file):
            cl_file = Path(__file__).parent / file_name

        assert os.path.exists(cl_file), (
            "Could not find OpenCL file: " + cl_file
        )

        kernel_str = open(cl_file).read()

        if not cl_dp:
            kernel_str = kernel_str.replace("double", "float")

        return kernel_str

    def _get_args_repr(self, *args, **kwargs) -> str:
        """
        Get a string representation of the args and kwargs
        """
        # print("Args: ", args)
        # print("Kwargs: ", kwargs)
        _args = []
        for arg in args:
            if type(arg) in (float, int):
                _args.append(f"number({arg})")
            elif hasattr(arg, "shape"):
                _args.append(f"shape{arg.shape}")
            else:
                _args.append(arg)
        _kwargs = {}
        for k, v in kwargs.items():
            if type(v) in (float, int):
                _kwargs[k] = f"number({v})"
            if hasattr(v, "shape"):
                _kwargs[k] = f"shape{arg.shape}"
            else:
                _kwargs[k] = v
        return repr((_args, _kwargs))

    def _get_args_shapes_numbers(self, txt: str):
        """
        Get the shapes and numbers from the string representation of the args and kwargs
        :param txt: the string representation of the args and kwargs
        :return: a tuple of the shapes and numbers
        """
        shapes = []
        numbers = []

        # example (['shape(3, 64, 32)', 'shape(3,)', 'shape(3,)', 'number(4.0)', 'number(4.0)'], {})

        # find shape values
        _txt = txt
        marker = 0
        while 1:
            start = _txt.find("shape(", marker)
            end = _txt.find(")", start)
            if start == -1 or end == -1:
                break
            elements = _txt[start + 6 : end].split(",")
            for element in elements:
                if element.strip() != "":
                    shapes.append(float(element))
            marker = end

        # find number values
        _txt = txt
        marker = 0
        while 1:
            start = _txt.find("number(", marker)
            end = _txt.find(")", start)
            if start == -1 or end == -1:
                break
            numbers.append(float(_txt[start + 7 : end]))
            marker = end

        return shapes, numbers

    def _get_args_score(self, txt: str) -> float:
        """
        Get the score for the given args and kwargs
        :param txt: the string representation of the args and kwargs
        :return: the score
        """
        shapes, numbers = self._get_args_shapes_numbers(txt)
        score = 1
        if len(shapes) > 0:
            score = score * np.prod(shapes)
        if len(numbers) > 0:
            score = score * np.prod(numbers)
        return score

    def _print(self, *args, **kwargs):
        """
        Prints the args and kwargs
        """
        if self._show_info:
            print(*args, **kwargs)

    ################
    # _run methods #
    ################

    def _run(self, *args, run_type=None, **kwargs):
        """
        Runs the function with the given args and kwargs
        :param args: args for the function
        :param run_type: the run type to use, if None use the fastest run type
        :param kwargs: kwargs for the function
        :return: the result of the function
        """

        if run_type is None:
            run_type = self._get_fastest_run_type(*args, **kwargs)
            self._print(
                f"Using run type: {self.RUN_TYPE_DESIGNATION[run_type]}"
            )

        t_start = time.time()
        if run_type == self.RUN_TYPE_OPENCL and self._has_opencl:
            r = self._run_opencl(*args, **kwargs)
        elif run_type == self.RUN_TYPE_UNTHREADED and self._has_unthreaded:
            r = self._run_unthreaded(*args, **kwargs)
        elif run_type == self.RUN_TYPE_THREADED and self._has_threaded:
            r = self._run_threaded(*args, **kwargs)
        elif (
            run_type == self.RUN_TYPE_THREADED_STATIC
            and self._has_threaded_static
        ):
            r = self._run_threaded_static(*args, **kwargs)
        elif (
            run_type == self.RUN_TYPE_THREADED_DYNAMIC
            and self._has_threaded_dynamic
        ):
            r = self._run_threaded_dynamic(*args, **kwargs)
        elif (
            run_type == self.RUN_TYPE_THREADED_GUIDED
            and self._has_threaded_guided
        ):
            r = self._run_threaded_guided(*args, **kwargs)
        elif run_type == self.RUN_TYPE_PYTHON and self._has_python:
            r = self._run_python(*args, **kwargs)
        elif run_type == self.RUN_TYPE_NJIT and self._has_njit:
            r = self._run_njit(*args, **kwargs)
        else:
            raise NotImplementedError("No run method defined")

        self._store_run_time(
            run_type,
            time.time() - t_start,
            *args,
            **kwargs,
        )
        self._last_run_type = run_type
        return r

    def _run_opencl(*args, **kwargs):
        """
        Runs the OpenCL version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_unthreaded(*args, **kwargs):
        """
        Runs the cython unthreaded version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_threaded(*args, **kwargs):
        """
        Runs the cython threaded version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_threaded_static(*args, **kwargs):
        """
        Runs the cython threaded static version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_threaded_dynamic(*args, **kwargs):
        """
        Runs the cython threaded dynamic version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_threaded_guided(*args, **kwargs):
        """
        Runs the cython threaded guided version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_python(*args, **kwargs):
        """
        Runs the python version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass

    def _run_njit(*args, **kwargs):
        """
        Runs the njit version of the function
        Should be overridden by the any class that inherits from this class
        """
        pass


def format_time(t: float):
    """
    Formats a time in seconds to a human readable string
    :param t: the time in seconds
    :return: a human readable string
    """
    if t < 1e-6:
        return f"{t * 1e9:.2f}ns"
    elif t < 1:
        return f"{t * 1000:.2f}ms"
    else:
        return f"{t:.2f}s"
