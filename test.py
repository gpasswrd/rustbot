import rustplus


def search_class(library, class_name, depth=0, visited=None):
    if visited is None:
        visited = set()

    if depth > 10:  # Set an arbitrary depth limit to avoid excessive recursion
        return None

    for submodule_name in dir(library):
        submodule = getattr(library, submodule_name)
        if isinstance(submodule, type(library)) and submodule not in visited:
            visited.add(submodule)

            if class_name in dir(submodule):
                return getattr(submodule, class_name)
            else:
                result = search_class(submodule, class_name, depth + 1, visited)
                if result:
                    return result

    return None

print(search_class(rustplus, "RustTeamMember"))