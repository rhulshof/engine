from cli.arg_parse import read_spec, spec_type_to_python_type
from modules.setup.config.cli import get_cli_config
from cli.print_utils import print_info, print_config_error


def validate_and_read_cli(config: dict, args):
    config_spec = read_spec()
    config.update(get_cli_config(args))
    validate_by_spec(config, config_spec)
    validate_single_currency_in_pairs(config)
    validate_fee(config)


def validate_by_spec(config, config_spec):
    for param_spec in config_spec:
        assert_given_else_default(config, param_spec)
        assert_type(config, param_spec)
        assert_in_options(config, param_spec)
        assert_min_max(config, param_spec)


def assert_given_else_default(config, spec):
    param_value = config.get(spec["name"])
    default = spec.get("default")
    if param_value is None and default is None:
        print_config_error(f"You must specify the '{spec['name']}' parameter")
    if param_value is None:
        config[spec["name"]] = default


def assert_type(config, spec):
    param_value = config.get(spec["name"])
    t = spec["type"]

    good = is_value_of_type(param_value, t)

    if not good:
        print_config_error(f"You passed an invalid type to the '{spec['name']}' parameter.")
        print_config_error(f"This type should be a(n) {t}, it is {type(param_value)}.")


def is_value_of_type(param_value, t):
    if t == "datetime":
        return True
    elif t == "number":
        return isinstance(param_value, int)
    elif t == "bool":
        return isinstance(param_value, bool)
    return True


def assert_min_max(config, spec):
    param_value = config.get(spec["name"])
    min_ = spec.get("min")
    max_ = spec.get("max")
    if min_ is not None and param_value < min_:
        print_config_error(f"{spec['name']} = {param_value} is under the minimum value {min_}.")
    if max_ is not None and param_value > max_:
        print_config_error(f"{spec['name']} = {param_value} is above the maximum value {max_}.")


def assert_in_options(config, spec):
    param_value = config.get(spec["name"])
    options = spec.get("options")
    if options is None:
        return
    if param_value not in options:
        print_config_error(f"spec['name'] = {param_value} is not a valid option, choose one from: "
                           f"{options}.")


def validate_single_currency_in_pairs(config: dict):
    """Checks whether every pair (e.g., BTC/USDT) contains
    the same currency as specified under the name 'currency'
    in the configuration.
    :param config: json configuration
    :type config: dict
    """
    pairs = config["pairs"]
    currency = config["currency"]
    for pair in pairs:
        pair = pair.split("/")
        assert len(pair) == 2
        if not pair[1] == currency:
            print_config_error("You can only use pairs that have the base currency you specified.")
            print_config_error("e.g., if you specified 'USDT' as your currency, you cannot add 'BTC/EUR' as a pair")


DEFAULT_FEE = 0.25
MAX_FEE = 0.5
MIN_FEE = 0.1


def validate_fee(config):
    try:
        input_fee = float(config["fee"])
    except ValueError:
        print_info(
            f"The inputted fee value is invalid, the algorithm will use the default value of {DEFAULT_FEE}% fee")
        return DEFAULT_FEE

    if input_fee > MAX_FEE:
        print_info(
            f"The inputted fee value is to big, the algorithm will use the default value of {MAX_FEE}% fee")
        return MAX_FEE
    elif input_fee < MIN_FEE:
        print_info(
            f"The inputted fee value is to small, the algorithm will use the default value of {MIN_FEE}% fee")
        return MIN_FEE

    print_info(
        f"The algorithm will use the inputted value of {input_fee}% as fee percentage.")

    config["fee"] = input_fee  # make sure its a float
