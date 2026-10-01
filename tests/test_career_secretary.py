import unittest

from game.careers import secretary as M
from tests.office_desk_cases import DeskCases


class SecretaryTests(DeskCases, unittest.TestCase):
    M = M


if __name__ == '__main__':
    unittest.main()
