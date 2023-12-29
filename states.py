from aiogram.dispatcher.filters.state import StatesGroup, State


class ProfileStatesGroup(StatesGroup):
    main_menu = State()
    number_of_incident = State()
    category_of_incident = State()
    description = State()
    priority = State()
    close_incident = State()
    edit_incident = State()
    edit_incident_kb = State()
    change_priority = State()
    recovery_incident = State()


