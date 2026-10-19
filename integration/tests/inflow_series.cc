#include <metric_flow_x/inflow_series.h>
#include <cassert>
#include <cmath>
#include <fstream>

int main()
{
  std::ofstream("inflow.csv") << "time_s,flow_m3_s\r\n0,0\r\n0.5,2e-6\r\n1,0\r\n";
  MetricFlowX::InflowSeries series;
  series.read("inflow.csv");
  assert(std::abs(series.value(.25) - 1e-6) < 1e-15);
  assert(series.value(0) == 0 && series.value(1) == 0);
  bool failed = false;
  try { series.value(1.1); } catch (const std::out_of_range &) { failed = true; }
  assert(failed);
  series.read("inflow.csv", 1.);
  assert(std::abs(series.value(1.25) - 1e-6) < 1e-15);
  assert(std::abs(series.value(-.25) - 1e-6) < 1e-15);
  std::ofstream("invalid.csv") << "time_s,flow_m3_s\n0,0\n0,1\n";
  failed = false;
  try { series.read("invalid.csv"); } catch (const std::invalid_argument &) { failed = true; }
  assert(failed);
}
