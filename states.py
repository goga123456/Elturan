from aiogram.dispatcher.filters.state import StatesGroup, State


class ProfileStatesGroup(StatesGroup):
    main_menu = State()
    number_of_incident = State()
    category_of_incident = State()
    category_hand = State()
    description = State()
    priority = State()
    close_incident = State()
    edit_incident = State()
    edit_incident_kb = State()
    change_priority = State()
    change_desc = State()
    recovery_incident = State()
    solve = State()
    cause = State()
    cause_yes = State()


