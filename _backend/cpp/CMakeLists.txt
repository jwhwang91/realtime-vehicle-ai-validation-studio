cmake_minimum_required(VERSION 3.16)
project(xcp_backend_mock LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(xcp_backend
    src/main.cpp
    src/can_driver_vector.cpp
    src/rx_thread.cpp
    src/tx_thread.cpp
    src/xcp_setup.cpp
    src/xcp_parser.cpp
    src/stim_writer.cpp
    src/config.cpp
)

target_include_directories(xcp_backend PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/vendor
)

target_compile_definitions(xcp_backend PRIVATE E2E_GUI_PUBLIC_MOCK=1)
