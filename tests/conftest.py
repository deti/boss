

def pytest_addoption(parser):
    parser.addoption("--test_config", action="store", help="System tests config path.")
    parser.addoption("--stage_config", action="store", help="Boss stage config path.")

