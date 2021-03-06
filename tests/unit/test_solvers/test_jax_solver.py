import pybamm
import unittest
from tests import get_mesh_for_testing
import sys
import time
import numpy as np
from platform import system


@unittest.skipIf(system() == "Windows", "JAX not supported on windows")
class TestJaxSolver(unittest.TestCase):
    def test_model_solver(self):
        # Create model
        model = pybamm.BaseModel()
        model.convert_to_format = "jax"
        domain = ["negative electrode", "separator", "positive electrode"]
        var = pybamm.Variable("var", domain=domain)
        model.rhs = {var: 0.1 * var}
        model.initial_conditions = {var: 1.0}
        # No need to set parameters; can use base discretisation (no spatial operators)

        # create discretisation
        mesh = get_mesh_for_testing()
        spatial_methods = {"macroscale": pybamm.FiniteVolume()}
        disc = pybamm.Discretisation(mesh, spatial_methods)
        disc.process_model(model)

        for method in ['BDF', 'RK45']:
            # Solve
            solver = pybamm.JaxSolver(
                method=method, rtol=1e-8, atol=1e-8
            )
            t_eval = np.linspace(0, 1, 80)
            t0 = time.perf_counter()
            solution = solver.solve(model, t_eval)
            t_first_solve = time.perf_counter() - t0
            np.testing.assert_array_equal(solution.t, t_eval)
            np.testing.assert_allclose(solution.y[0], np.exp(0.1 * solution.t),
                                       rtol=1e-7, atol=1e-7)

            # Test time
            self.assertEqual(
                solution.total_time, solution.solve_time + solution.set_up_time
            )
            self.assertEqual(solution.termination, "final time")

            t0 = time.perf_counter()
            second_solution = solver.solve(model, t_eval)
            t_second_solve = time.perf_counter() - t0

            self.assertLess(t_second_solve, t_first_solve)
            np.testing.assert_array_equal(second_solution.y, solution.y)

    def test_solver_only_works_with_jax(self):
        model = pybamm.BaseModel()
        var = pybamm.Variable("var")
        model.rhs = {var: -pybamm.sqrt(var)}
        model.initial_conditions = {var: 1}
        # No need to set parameters; can use base discretisation (no spatial operators)

        # create discretisation
        disc = pybamm.Discretisation()
        disc.process_model(model)

        t_eval = np.linspace(0, 3, 100)

        # solver needs a model converted to jax
        for convert_to_format in ["casadi", "python", "something_else"]:
            model.convert_to_format = convert_to_format

            solver = pybamm.JaxSolver()
            with self.assertRaisesRegex(RuntimeError, "must be converted to JAX"):
                solver.solve(model, t_eval)

    def test_solver_doesnt_support_events(self):
        # Create model
        model = pybamm.BaseModel()
        model.convert_to_format = "jax"
        domain = ["negative electrode", "separator", "positive electrode"]
        var = pybamm.Variable("var", domain=domain)
        model.rhs = {var: -0.1 * var}
        model.initial_conditions = {var: 1}
        # needs to work with multiple events (to avoid bug where only last event is
        # used)
        model.events = [
            pybamm.Event("var=0.5", pybamm.min(var - 0.5)),
            pybamm.Event("var=-0.5", pybamm.min(var + 0.5)),
        ]
        # No need to set parameters; can use base discretisation (no spatial operators)

        # create discretisation
        mesh = get_mesh_for_testing()
        spatial_methods = {"macroscale": pybamm.FiniteVolume()}
        disc = pybamm.Discretisation(mesh, spatial_methods)
        disc.process_model(model)
        # Solve
        solver = pybamm.JaxSolver()
        t_eval = np.linspace(0, 10, 100)
        with self.assertRaisesRegex(RuntimeError, "Terminate events not supported"):
            solver.solve(model, t_eval)

    def test_model_solver_with_inputs(self):
        # Create model
        model = pybamm.BaseModel()
        model.convert_to_format = "jax"
        domain = ["negative electrode", "separator", "positive electrode"]
        var = pybamm.Variable("var", domain=domain)
        model.rhs = {var: -pybamm.InputParameter("rate") * var}
        model.initial_conditions = {var: 1}
        # No need to set parameters; can use base discretisation (no spatial
        # operators)

        # create discretisation
        mesh = get_mesh_for_testing()
        spatial_methods = {"macroscale": pybamm.FiniteVolume()}
        disc = pybamm.Discretisation(mesh, spatial_methods)
        disc.process_model(model)
        # Solve
        solver = pybamm.JaxSolver(rtol=1e-8, atol=1e-8)
        t_eval = np.linspace(0, 5, 100)

        t0 = time.perf_counter()
        solution = solver.solve(model, t_eval, inputs={"rate": 0.1})
        t_first_solve = time.perf_counter() - t0

        np.testing.assert_allclose(solution.y[0], np.exp(-0.1 * solution.t),
                                   rtol=1e-6, atol=1e-6)

        t0 = time.perf_counter()
        solution = solver.solve(model, t_eval, inputs={"rate": 0.2})
        t_second_solve = time.perf_counter() - t0

        np.testing.assert_allclose(solution.y[0], np.exp(-0.2 * solution.t),
                                   rtol=1e-6, atol=1e-6)

        self.assertLess(t_second_solve, t_first_solve)

    def test_get_solve(self):
        # Create model
        model = pybamm.BaseModel()
        model.convert_to_format = "jax"
        domain = ["negative electrode", "separator", "positive electrode"]
        var = pybamm.Variable("var", domain=domain)
        model.rhs = {var: -pybamm.InputParameter("rate") * var}
        model.initial_conditions = {var: 1}
        # No need to set parameters; can use base discretisation (no spatial
        # operators)

        # create discretisation
        mesh = get_mesh_for_testing()
        spatial_methods = {"macroscale": pybamm.FiniteVolume()}
        disc = pybamm.Discretisation(mesh, spatial_methods)
        disc.process_model(model)
        # Solve
        solver = pybamm.JaxSolver(rtol=1e-8, atol=1e-8)
        t_eval = np.linspace(0, 5, 100)

        with self.assertRaisesRegex(RuntimeError, "Model is not set up for solving"):
            solver.get_solve(model, t_eval)

        solver.solve(model, t_eval, inputs={"rate": 0.1})
        solver = solver.get_solve(model, t_eval)
        y, _ = solver({"rate": 0.1})

        np.testing.assert_allclose(y[0], np.exp(-0.1 * t_eval),
                                   rtol=1e-6, atol=1e-6)

        y, _ = solver({"rate": 0.2})

        np.testing.assert_allclose(y[0], np.exp(-0.2 * t_eval),
                                   rtol=1e-6, atol=1e-6)


if __name__ == "__main__":
    print("Add -v for more debug output")

    if "-v" in sys.argv:
        debug = True
    pybamm.settings.debug_mode = True
    unittest.main()
