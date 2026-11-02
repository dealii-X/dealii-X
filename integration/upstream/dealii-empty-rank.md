## Reproduction

While testing the deal.II-X MetricFlowX circulation model with tabulated inflow,
SUNDIALS IDA consistent initialization fails with two MPI ranks when the initial
mesh has one cell and one rank owns no vector entries. The same executable and
input run with one rank. With eight initial cells distributed between two ranks,
the two-rank run also succeeds.

Environment: macOS ARM64, installed deal.II `9.8.0-rc1`, PETSc MPI vectors,
SUNDIALS 6.7.0, MPICH. The checked source at `4183653650` also contains the
unguarded implementation described below; current master should be checked
before applying a fix.

## Observed failure

`PETScWrappers::internal::VectorReference::operator double()` reports an access
to element -1 on a rank with no locally owned elements. The stack passes through
`SUNDIALS::internal::NVectorOperations::min_element<PETScWrappers::MPI::Vector>()`
and `IDACalcIC`.

## Suspected cause and requested change

The distributed, non-block `min_element` implementation in
`include/deal.II/sundials/n_vector.templates.h` dereferences `std::min_element`
without checking whether `locally_owned_elements()` is empty. Return the neutral
local minimum (`numeric_limits<realtype>::max()`) on empty ranks before the global
minimum reduction, as appropriate for the SUNDIALS contract. The distributed
block-vector path already guards its iterator.

Please add a regression using a distributed vector with at least one empty rank
and verify the global minimum and IDA initialization. This is independent of the
CSV interpolation code: the failure occurs inside the vector operation.
