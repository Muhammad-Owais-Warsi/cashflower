Advanced
========

Array variables
---------------

In cashflower, another type of variable is the array variable. Array variables can be defined by decorating a function
with the :code:`@variable` decorator, with the :code:`array` parameter set to :code:`True`.

For example:

.. code-block:: python

    @variable(array=True)
    def pv_net_cf():
        return pv_premiums() - pv_claims() - pv_expenses()

Array variables significantly optimize calculation runtimes by leveraging the powerful NumPy package
and its broadcasting mechanism. Instead of performing calculations for each period separately, array variables compute
results in a single operation for the entire variable.

However, array variables can introduce higher complexity in your formulas.

|

Construction
^^^^^^^^^^^^

Consider this array variable example:

.. code-block:: python

    from settings import settings

    @variable(array=True)
    def array_var():
        return [x for x in range(settings["T_MAX_CALCULATION"]+1)]

Breaking down each line:

.. code-block:: python

    @variable(array=True)

Array variables use the :code:`@variable` decorator, but they require setting the :code:`array` parameter to :code:`True`.

.. code-block:: python

    def array_var():

The function does not take the :code:`t` parameter; it remains empty.

.. code-block:: python

    return [x for x in range(settings["T_MAX_CALCULATION"]+1)]

The array variable should return a numeric iterable of a size equal to the :code:`T_MAX_CALCULATION` setting
(by default 721). This iterable will be internally converted to a NumPy array of type float64.

|

Regular variables results
^^^^^^^^^^^^^^^^^^^^^^^^^

You can create array variables using results of regular variables:

.. code-block:: python

    @variable(array=True)
    def pv_net_cf():
        return pv_premiums() - pv_claims() - pv_expenses()

To obtain the full results of a variable, call it without the :code:`t` argument.
For example, :code:`pv_premiums` is a regular t-dependent variable:

.. code-block:: python

    @variable()
    def pv_premiums(t):
        if t == settings["T_MAX_CALCULATION"]:
            return premiums(t) * discount(t)
        return premiums(t) * discount(t) + pv_premiums(t+1)

Calling :code:`pv_premiums` with a specific :code:`t` value returns the result for that period:

.. code-block:: python

    print(pv_premiums(t=10))
    # 126.12

But calling :code:`pv_premiums` without any argument will return the NumPy array of results:

.. code-block:: python

    print(pv_premium())
    # np.array([145.45, 142.37, ..., 9.35])

The results are based on NumPy arrays, so they utilize the broadcasting mechanism.
That's why they can be used in the creation of :code:`pv_net_cf`.

|

Limitations for cycles
^^^^^^^^^^^^^^^^^^^^^^

Variables cannot be arrayized if they are part of a cycle. A cycle refers to a group of variables that depend on
each other cyclically. For example:

.. code-block:: python

    @variable()
    def a(t):
        return 2 * b(t)


    @variable()
    def b(t):
        if t == 0:
            return 0
        return c(t-1)


    @variable()
    def c(t):
        return a(t) + 2

Here variable :code:`a` depends on variable :code:`b`. Variable :code:`b` depends on :code:`c` and
variable :code:`c` depends on variable :code:`a`.

You can identify variables that are part of a cycle by inspecting the diagnostic file.

.. WARNING::
    Variables that are part of a cycle cannot be array variables.

|

Usage
^^^^^

Array variables offer improved runtime performance compared to regular variables but come with increased complexity
in their construction. The decision of whether to use array variables ultimately rests with the actuarial modeler.
If your model has a limited number of model points, and runtime is satisfactory, it may be best to stick with regular
variables for readability.

On the other hand, if runtime is critical, array variables can be beneficial. It's advisable to start arrayizing
variables with simple logic, such as those that involve only addition or multiplication of other variables or scalars.

|

Comparison
^^^^^^^^^^

1. Regular variables

.. code-block:: python

    @variable()
    def regular_var(t):
        return t

    print(regular_var(5))
    # 5.0

    print(regular_var())
    # np.array([0., 1., 2., ..., 72.])

2. Constant variables

.. code-block:: python

    @variable()
    def constant_var():
        return 1

    print(constant_var(5))
    # 1.0

    print(constant_var())
    # 1.0

3. Array variables

.. code-block:: python

    @variable(array=True)
    def array_var():
        return [*range(720)]

    print(array_var(5))
    # 5.0

    print(array_var())
    # np.array([0., 1., 2., ..., 72.])

|

Discount function
-----------------

Discounting is a common calculation in the actuarial cash flow models.
The :code:`discount()` function available in the package supports the vectorized approach to discounting.

.. code-block:: python

    from cashflower import discount

    @variable(array=True)
    def present_value():
        return discount(cash_flows=cash_flow(), discount_rates=discount_rate())


The :code:`discount()` function takes two mandatory parameters, both of which must be NumPy arrays containing float values:

* :code:`cash_flows` - an array representing the cash flows to be discounted,
* :code:`discount_rates`- an array of forward discount rates corresponding to each period.

The :code:`discount()` function returns an array, so you can specify :code:`@variable(array=True)` for the variable that will hold the result.

|

Scalar equivalent
^^^^^^^^^^^^^^^^^

The :code:`discount()` function's calculation is equivalent to the following recursive formula:

.. code-block:: python

    from settings import settings

    @variable()
    def present_value(t):
        if t == settings["T_MAX_CALCULATION"]:
            return cash_flow(t)
        else:
            return cash_flow(t) + present_value(t+1) * cash_flow(t+1)

Using the :code:`discount()` function significantly improves the calculation time.

|

Calculation example
^^^^^^^^^^^^^^^^^^^

Here's an example of how the :code:`discount()` function works:

.. code-block:: python

    import numpy as np
    from cashflower import discount

    cash_flow = np.array([90.00, 120.00, 100.00])
    discount_rate = np.array([1, 0.8, 0.9])
    print(discount(cash_flow, discount_rate))
    # [258. 210. 100.]

In this example, the present values of future cash flows for three periods are calculated as follows:

* :code:`258.0` is the present value of all three cash flows at the beginning of projection :code:`90.0 + 120.0 * 0.8 + 100.0 * 0.8 * 0.9`.
* :code:`210.0` is the present value of two cashflows after the first period :code:`120.0 + 100.0 * 0.9`.
* :code:`100.0` represents the present value of the last cash flow after two periods :code:`100.0`.

Note that the discount rate at time :code:`t` represents the value of :code:`1` at time :code:`t-1`.
