"""Our preference: which children a narrator makes narrators, and which it makes actors.

The real world has no tree, so this is where we cut it. A narrator plans for a part and briefs the
people in it; an actor decides alone. The chosen option's TEXT goes into the narrator's system
prompt where the template says {{child_roles}}. How deep the tree grows follows from this rule and
the narrators' own choices, not from a level count.
"""

from typing import Literal

ChildRoles = Literal[
    # Default. Narrators only for groups inside the narrator's part, such as a company's
    # departments or a household. Outside parties with a deal of their own (customers, vendors,
    # landlords) are always actors, so a company's tree stops at company, departments, people.
    "inside_parts",
    # Any group whose several people will each act in the story is a narrator, inside the
    # narrator's part or outside it: a customer whose payment passes through its own controller
    # and approver, an employee's household. One person, or a business that acts with one voice,
    # is an actor. The tree goes as deep as the people who act.
    "any_group",
]

DEFAULT: ChildRoles = "inside_parts"

TEXT: dict[ChildRoles, str] = {
    "inside_parts": (
        "Make a child a narrator when its part holds several people or parties of its own, such "
        "as a company, a department or a household. Make it an actor when it is one person or "
        "one business acting for itself, such as an employee, a customer, a vendor or a landlord."
    ),
    "any_group": (
        "Make a child a narrator when its part holds several people of its own who will each do "
        "something in the story, whether the part sits inside yours or outside it: a department, "
        "a household, a customer whose payments pass through its own controller, approver and "
        "clerk, a vendor whose billing and collections people act separately. Make it an actor "
        "when one person, or a business that acts with one voice, does all of its acting. Decide "
        "each child by who in it will act, the way the real world is arranged, not by how many "
        "levels the tree already has."
    ),
}
