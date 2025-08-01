# SPDX-FileCopyrightText: Copyright (c) 2023-2025, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Script to customize doxygen/sphinx generated HTML for RAPIDS
"""

import re
import sys
import json
import os
from bs4 import BeautifulSoup
from util import r_versions

FILEPATH = sys.argv[1]
IS_UCXX_FILE = len(sys.argv) > 2 and sys.argv[2] == "--is-ucxx"

LIB_MAP_PATH = os.path.join(os.path.dirname(__file__), "lib_map.json")
RELEASES_PATH = os.path.join(
    os.path.dirname(__file__), "../", "../", "_data", "releases.json"
)

with open(LIB_MAP_PATH) as fp:
    LIB_PATH_DICT = json.load(fp)

with open(RELEASES_PATH) as fp:
    release_data = json.load(fp)
    VERSIONS_DICT = {
        "nightly": release_data["nightly"][
            "ucxx_version" if IS_UCXX_FILE else "version"
        ],
        "stable": release_data["stable"]["ucxx_version" if IS_UCXX_FILE else "version"],
        "legacy": release_data["legacy"]["ucxx_version" if IS_UCXX_FILE else "version"],
    }

SCRIPT_TAG_ID = "rapids-selector-js"
PIXEL_SRC_TAG_ID = "rapids-selector-pixel-src"
PIXEL_INVOCATION_TAG_ID = "rapids-selector-pixel-invocation"
STYLE_TAG_ID = "rapids-selector-css"
FA_TAG_ID = "rapids-fa-tag"


def get_version_from_fp():
    """
    Determines if the current HTML document is for legacy, stable, or nightly versions
    based on the file path
    """
    match = re.search(r"/(\d?\d\.\d\d)/", FILEPATH)
    version_number_str = r_versions(match.group(1))
    version_name = "stable"
    if version_number_str.is_greater_than(VERSIONS_DICT["stable"]):
        version_name = "nightly"
    if version_number_str.is_less_than(VERSIONS_DICT["stable"]):
        version_name = "legacy"
    return {"name": version_name, "number": version_number_str}


def get_lib_from_fp():
    """
    Determines the current RAPIDS library based on the file path
    """

    for lib in LIB_PATH_DICT.keys():
        if re.search(f"(^{lib}/|/{lib}/)", FILEPATH):
            return lib
    raise Exception(f"Couldn't find valid library name in {FILEPATH}.")


def create_home_container(soup):
    """
    Creates and returns a div with a Home button and icon in it
    """
    container = soup.new_tag("div", attrs={"class": "rapids-home-container"})
    home_btn = soup.new_tag("a", attrs={"class": "rapids-home-container__home-btn"})
    home_btn["href"] = "/api"
    home_btn.string = "Home"
    container.append(home_btn)
    return container


def add_font_awesome(soup):
    """
    Adds a font-awesome to the head of the HTML
    """
    fa_tag = soup.new_tag(
        "link",
        attrs={
            "href": "https://stackpath.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
            "rel": "stylesheet",
            "id": FA_TAG_ID,
        },
    )
    soup.head.append(fa_tag)


def create_version_options():
    """
    Creates options for legacy/stable/nightly selector
    """
    options = []
    doc_version = get_version_from_fp()
    doc_lib = get_lib_from_fp()
    doc_is_extra_legacy = (  # extra legacy means the doc version is older then current legacy
        doc_version["name"] == "legacy"
        and VERSIONS_DICT["legacy"] != doc_version["number"]
    )
    doc_is_extra_nightly = (  # extra nightly means the doc version is newer then current nightly
        doc_version["name"] == "nightly"
        and VERSIONS_DICT["nightly"] != doc_version["number"]
    )
    for version_name, version_path in [
        (_, path) for _, path in LIB_PATH_DICT[doc_lib].items() if path is not None
    ]:
        if (doc_is_extra_legacy and version_name == "legacy") or (
            doc_is_extra_nightly and version_name == "nightly"
        ):
            version_number_str = doc_version["number"]
        else:
            version_number_str = VERSIONS_DICT[version_name]
        is_selected = False
        option_href = version_path
        version_text = f"{version_name} ({version_number_str})"
        if version_name == doc_version["name"]:
            print(f"default version: {version_name}")
            is_selected = True
        options.append(
            {"selected": is_selected, "href": option_href, "text": version_text}
        )

    return options


def create_library_options():
    """
    Creates options for library selector
    """
    doc_lib = get_lib_from_fp()
    options = []

    for lib, lib_versions in LIB_PATH_DICT.items():
        if lib_versions["stable"]:
            option_href = lib_versions["stable"]
        elif lib_versions["nightly"]:
            option_href = lib_versions["nightly"]
        elif lib_versions["legacy"]:
            option_href = lib_versions["legacy"]
        else:
            continue
        is_selected = False
        if lib == doc_lib:
            print(f"default lib: {lib}")
            is_selected = True
        options.append({"selected": is_selected, "href": option_href, "text": lib})

    return options


def create_selector(soup, options):
    """
    Creates a dropdown selector
    """
    container = soup.new_tag(
        "div",
        attrs={"class": ["rapids-selector__container", "rapids-selector--hidden"]},
    )
    selected = soup.new_tag("div", attrs={"class": "rapids-selector__selected"})
    selected.string = next(option["text"] for option in options if option["selected"])
    container.append(selected)
    drop_down_menu = soup.new_tag("div", attrs={"class": ["rapids-selector__menu"]})

    for option in options:
        option_classes = ["rapids-selector__menu-item"]
        if option["selected"]:
            option_classes.append("rapids-selector__menu-item--selected")
        option_el = soup.new_tag(
            "a", href=option["href"], attrs={"class": option_classes}
        )
        option_el.string = option["text"]
        drop_down_menu.append(option_el)

    container.append(drop_down_menu)
    return container


def create_script_tag(soup):
    """
    Creates and returns a script tag that points to custom.js
    """
    script_tag = soup.new_tag(
        "script", defer=None, id=SCRIPT_TAG_ID, src="/assets/js/custom.js"
    )
    return script_tag


def create_pixel_tags(soup):
    """
    Creates and returns the pixel script tags
    """

    head_tag = soup.new_tag(
        "script",
        id=PIXEL_SRC_TAG_ID,
        src="https://assets.adobedtm.com/5d4962a43b79/814eb6e9b4e1/launch-4bc07f1e0b0b.min.js",
    )
    body_tag = soup.new_tag(
        "script",
        type="text/javascript",
        id=PIXEL_INVOCATION_TAG_ID,
    )
    body_tag.string = "_satellite.pageBottom();"
    return [head_tag, body_tag]


def create_css_link_tag(soup):
    """
    Creates and returns a link tag that points to custom.css
    """
    script_tag = soup.new_tag(
        "link", id=STYLE_TAG_ID, rel="stylesheet", href="/assets/css/custom.css"
    )
    return script_tag


def delete_element(soup, selector):
    """
    Deletes element from soup object if it already exists
    """
    try:
        soup.select(f"{selector}")[0].extract()
    except Exception:
        pass


def delete_existing_elements(soup):
    """
    Deletes any existing page elements to prevent duplicates on the page
    """
    doxygen_title_area = "#titlearea > table"
    sphinx_home_btn = ".wy-side-nav-search .icon.icon-home"
    sphinx_doc_version = ".wy-side-nav-search .version"
    existing_jtd_container = "#rapids-jtd-container"
    existing_pydata_container = "#rapids-pydata-container"
    existing_doxygen_container = "#rapids-doxygen-container"

    for element in [
        existing_jtd_container,
        existing_pydata_container,
        existing_doxygen_container,
        sphinx_doc_version,
        sphinx_home_btn,
        doxygen_title_area,
        f"#{SCRIPT_TAG_ID}",
        f"#{STYLE_TAG_ID}",
        f"#{FA_TAG_ID}",
        f"#{PIXEL_SRC_TAG_ID}",
        f"#{PIXEL_INVOCATION_TAG_ID}",
    ]:
        delete_element(soup, element)


def get_theme_info(soup):
    """
    Determines what theme a given HTML file is using or exits if it's
    not able to be determined. Returns a string identifier and reference element
    that is used for inserting the library/version selectors to the doc.
    """
    # Sphinx Themes
    jtd_identifier = ".wy-side-nav-search"  # Just-the-docs theme
    pydata_identifier = ".bd-sidebar"  # Pydata theme

    # Doxygen
    doxygen_identifier = "#titlearea"

    if soup.select(jtd_identifier):
        return "jtd", soup.select(jtd_identifier)[0]

    if soup.select(doxygen_identifier):
        return "doxygen", soup.select(doxygen_identifier)[0]

    if soup.select(pydata_identifier):
        return "pydata", soup.select(pydata_identifier)[0]

    print(
        f"Couldn't identify {FILEPATH} as a supported theme type. Skipping file.",
        file=sys.stderr,
    )
    exit(0)


def main():
    """
    Given the path to a documentation HTML file, this function will
    parse the file and add library/version selectors and a Home button
    """
    print(f"--- {FILEPATH} ---")
    with open(FILEPATH) as fp:
        soup = BeautifulSoup(fp, "html5lib")

    doc_type, reference_el = get_theme_info(soup)

    # Delete any existing added/unnecessary elements
    delete_existing_elements(soup)

    # Add Font Awesome to Doxygen for icons
    if doc_type == "doxygen":
        add_font_awesome(soup)

    # Create new elements
    home_btn_container = create_home_container(soup)
    library_selector = create_selector(soup, create_library_options())
    version_selector = create_selector(soup, create_version_options())
    container = soup.new_tag("div", id=f"rapids-{doc_type}-container")
    script_tag = create_script_tag(soup)
    [pix_head_tag, pix_body_tag] = create_pixel_tags(soup)
    style_tab = create_css_link_tag(soup)

    # Append elements to container
    container.append(home_btn_container)
    container.append(library_selector)
    container.append(version_selector)

    # Insert new elements
    reference_el.insert(0, container)
    soup.body.append(script_tag)
    soup.body.append(pix_body_tag)
    soup.head.append(pix_head_tag)
    soup.head.append(style_tab)

    with open(FILEPATH, "w") as fp:
        fp.write(soup.decode(formatter="html5"))


if __name__ == "__main__":
    main()
