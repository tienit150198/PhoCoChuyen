import unittest

from game.careers import hr_admin as M
from tests.office_desk_cases import DeskCases


class HrAdminTests(DeskCases, unittest.TestCase):
    M = M


if __name__ == '__main__':
    unittest.main()
