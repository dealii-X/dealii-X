cmake_minimum_required(VERSION 3.35)

set(CMAKE_BUILD_TYPE Debug)
find_package(deal.II 9.6.0
  HINTS ${deal.II_DIR} ${DEAL_II_DIR} ../ ../../ $ENV{DEAL_II_DIR}
  )
DEAL_II_PICKUP_TESTS()
