import ast
from argparse import ArgumentParser

from src.PipelineFactory import PipelineFactory


class CLI:
    def main(self):
        program_name = "CASCADE"
        description = ""
        epilog = "To overwrite key word arguments one has to write \"key:value\", except for the filters, where one has to write \"(index,key:value)\""
        arg_parser = ArgumentParser(prog=program_name,
                                    description=description,
                                    epilog=epilog)

        arg_parser.add_argument('-i', '--input-path', required=True, help="The input path which will be used for extraction")
        arg_parser.add_argument('-o', '--output-path', required=True, help="The output path in which results and temporary files will be stored")
        arg_parser.add_argument('-s', '--setup-file', required=True, help="The path to the setup file defining the pipeline")
        arg_parser.add_argument('-m', '--module-path', help="The path to the user defined modules.")
        arg_parser.add_argument('-extr', '--extraction', action="append", help="A way to overwrite the key word arguments for the extraction.")
        arg_parser.add_argument('-codegen', '--code-generator', action="append", help="A way to overwrite the key word arguments for the code generator.")
        arg_parser.add_argument('-testgen', '--test-generator', action="append", help="A way to overwrite the key word arguments for the test generator.")
        arg_parser.add_argument('-docgen', '--doc-generator', action="append", help="A way to overwrite the key word arguments for the doc generator.")
        arg_parser.add_argument('-ana', '--analysis', action="append", help="A way to overwrite the key word arguments for the analysis.")
        arg_parser.add_argument('-exec', '--executor', action="append", help="A way to overwrite the key word arguments for the executor.")
        arg_parser.add_argument('-visua', '--visualizer', action="append", help="A way to overwrite the key word arguments for the visualizer.")
        arg_parser.add_argument('-filter', '--filters', action="append", help="A way to overwrite the key word arguments for the filters.")

        arg_parser.add_argument('--debug-cli', help="Shows debug information for the CLI call.")

        #arg_parser.parse_args(args=["-h"])
        args = arg_parser.parse_args()

        kwargs_overrides = {"Extraction": {}, "CodeGenerator": {}, "TestGenerator": {}, "DocGenerator": {}, "Analysis": {}, "Executor": {}, "Visualizer": {}, "FilterFunctions": []}
        override_to_arg = {"Extraction": args.extraction, "CodeGenerator": args.code_generator, "TestGenerator": args.test_generator, "DocGenerator": args.doc_generator, "Analysis": args.analysis, "Executor": args.executor, "Visualizer": args.visualizer}
        for key, value in override_to_arg.items():
            if value:
                for kw in value:
                    try:
                        key_value = kw.split(":")

                        try:
                            kwargs_overrides[key][key_value[0]] = ast.literal_eval(key_value[1])
                        except:
                            kwargs_overrides[key][key_value[0]] = key_value[1]

                    except Exception as e:
                        print(e)
        if args.filters:
            for tuple_ in args.filters:
                try:
                    index = int(tuple_[1:-1].split(",")[0])
                    key_value = (",".join(tuple_[1:-1].split(",")[1:])).split(":")
                    filters = kwargs_overrides["FilterFunctions"]
                    while len(filters) <= index:
                        filters.append({})
                    try:
                        filters[index][key_value[0].strip()] = ast.literal_eval(key_value[1])
                    except:
                        filters[index][key_value[0].strip()] = key_value[1]

                except Exception as e:
                    print(e)
        kwargs_ = {}
        kwargs_["module_path"] = args.module_path
        kwargs_.update(kwargs_overrides)
        if args.debug_cli:
            print("kwargs", kwargs_)

        factory = PipelineFactory()
        pipeline = factory.build(args.setup_file, kwargs_)
        pipeline.execute(args.input_path, args.output_path)


if __name__ == '__main__':
    cli = CLI()
    cli.main()

