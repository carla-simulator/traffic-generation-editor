## OpenSCENARIO Tags Support

Based on [OpenSCENARIO 1.0.0](https://releases.asam.net/OpenSCENARIO/1.0.0/Model-Documentation/RenderedXsdOutput.html)

- [OpenSCENARIO Tags Support](#openscenario-tags-support)
- [File Header](#file-header)
- [Catalog](#catalog)
- [Parameter Declarations](#parameter-declarations)
- [Road Network](#road-network)
- [Entities](#entities)
  - [Scenario Object - Vehicle](#scenario-object---vehicle)
  - [Scenario Object - Pedestrian](#scenario-object---pedestrian)
  - [Scenario Object - MiscObject](#scenario-object---miscobject)
- [Actions - Global Actions](#actions---global-actions)
- [Actions - User Defined Actions](#actions---user-defined-actions)
- [Actions - Private Actions](#actions---private-actions)
- [Start / Stop Conditions - By Entity](#start--stop-conditions---by-entity)
- [Start / Stop Conditions - By Value](#start--stop-conditions---by-value)

## File Header
| Tag         | Import | Export | Remarks                                |
| ----------- | :----: | :----: | -------------------------------------- |
| revMajor    |   ❌    |   🟡    | Exports constant value                 |
| revMinor    |   ❌    |   🟡    | Exports constant value                 |
| date        |   ❌    |   🟡    | Exports time and date of file creation |
| description |   ❌    |   🟡    | Exports constant value                 |
| author      |   ❌    |   🟡    | Exports constant value                 |

## Catalog
❌ Catalog references are currently not supported for import and export

## Parameter Declarations
⚠️ _Note: Local parameters are currently not supported, only global parameters._
| Tag                  | Import | Export | Remarks                    |
| -------------------- | :----: | :----: | -------------------------- |
| ParameterDeclaration |   ✅    |   ✅    | Only for global parameters |

## Road Network
| Tag                     | Import | Export | Remarks                                                |
| ----------------------- | :----: | :----: | ------------------------------------------------------ |
| LogicFile               |   ✅    |   ✅    | On import, will save information into `Metadata` layer |
| SceneGraphFile          |   ❌    |   ❌    | Exports blank filepath                                 |
| TrafficSignals          |   ❌    |   ❌    |
| TrafficSignalController |   ❌    |   ❌    |

## Entities
| Tag              | Import | Export | Remarks                                   |
| ---------------- | :----: | :----: | ----------------------------------------- |
| ScenarioObject   |   ✅    |   ✅    | Entity `name` is not preserved on import  |
| ObjectController |   ❌    |   ❌    |
| CatalogReference |   ❌    |   ❌    | `CatalogReference` for `ObjectController` |
| Controller       |   ❌    |   ❌    |
| CatalogReference |   ❌    |   ❌    | `CatalogReference` for `ScenarioObject`   |

### Scenario Object - Vehicle
| Tag                   | Import | Export | Remarks                                        |
| --------------------- | :----: | :----: | ---------------------------------------------- |
| ParameterDeclarations |   ❌    |   ❌    | Only global parameters are supported           |
| BoundingBox           |   🟡    |   🟡    | Exports constant value                         |
| Performance           |   🟡    |   🟡    | Exports constant value                         |
| Axles                 |   🟡    |   🟡    | Exports constant value                         |
| Properties            |   🟡    |   🟡    | Exports `ego_vehicle` if it is ego, else empty |

### Scenario Object - Pedestrian
| Tag                   | Import | Export | Remarks                              |
| --------------------- | :----: | :----: | ------------------------------------ |
| ParameterDeclarations |   ❌    |   ❌    | Only global parameters are supported |
| BoundingBox           |   🟡    |   🟡    | Exports constant value               |
| Performance           |   🟡    |   🟡    | Exports constant value               |

### Scenario Object - MiscObject
| Tag                   | Import | Export | Remarks                              |
| --------------------- | :----: | :----: | ------------------------------------ |
| ParameterDeclarations |   ❌    |   ❌    | Only global parameters are supported |
| BoundingBox           |   🟡    |   🟡    | Exports constant value               |
| Performance           |   🟡    |   🟡    | Exports constant value               |

## Actions - Global Actions
| Tag                  | Import | Export | Remarks                 |
| -------------------- | :----: | :----: | ----------------------- |
| EnvironmentActions   |   ✅    |   ✅    |
| EntityAction         |   ❌    |   ❌    |
| ParameterAction      |   ❌    |   ❌    |
| InfrastructureAction |   ✅    |   ✅    | Controls traffic lights |
| TrafficAction        |   ❌    |   ❌    |

## Actions - User Defined Actions
| Tag                 | Import | Export | Remarks |
| ------------------- | :----: | :----: | ------- |
| CustomCommandAction |   ❌    |   ❌    |

## Actions - Private Actions
| Tag                                             | Import | Export | Remarks                           |
| ----------------------------------------------- | :----: | :----: | --------------------------------- |
| LongitudinalAction / SpeedAction                |   ✅    |   ✅    |
| LongitudinalAction / LongitudinalDistanceAction |   ✅    |   ✅    |
| LateralAction / LaneChangeAction                |   ✅    |   ✅    |
| LateralAction / LaneOffsetAction                |   ✅    |   ✅    |
| LateralAction / LateralDistanceAction           |   ✅    |   ✅    |
| VisibilityAction                                |   ❌    |   ❌    |
| SynchronizeAction                               |   ❌    |   ❌    |
| ActivateControllerAction                        |   ❌    |   ❌    |
| ControllerAction / AssignControllerAction       |   ✅    |   ✅    |
| ControllerAction / OverrideControllerAction     |   🟡    |   🟡    | Exports pre-determined values     |
| TeleportAction                                  |   🟡    |   🟡    | Only `WorldPosition` is supported |
| RoutingAction / AssignRouteAction               |   ✅    |   ✅    |
| RoutingAction / FollowTrajectoryAction          |   ❌    |   ❌    |
| RoutingAction / AcquitePositionAction           |   ❌    |   ❌    |

## Start / Stop Conditions - By Entity
| Tag                       | Import | Export | Remarks |
| ------------------------- | :----: | :----: | ------- |
| EndOfRoadCondition        |   ✅    |   ✅    |
| CollisionCondition        |   ✅    |   ✅    |
| OffroadCondition          |   ✅    |   ✅    |
| TimeHeadwayCondition      |   ✅    |   ✅    |
| AccelerationCondition     |   ✅    |   ✅    |
| StandStillCondition       |   ✅    |   ✅    |
| SpeedContidion            |   ✅    |   ✅    |
| RelativeSpeedCondition    |   ✅    |   ✅    |
| TraveledDistanceCondition |   ✅    |   ✅    |
| ReachPositionCondition    |   ✅    |   ✅    |
| DistanceCondition         |   ✅    |   ✅    |
| RelativeDistanceCondition |   ✅    |   ✅    |

## Start / Stop Conditions - By Value
| Tag                              | Import | Export | Remarks                                           |
| -------------------------------- | :----: | :----: | ------------------------------------------------- |
| ParameterCondition               |   ✅    |   ✅    |
| TimeOfDayCondition               |   ✅    |   ✅    |
| SimulationTimeCondition          |   ✅    |   ✅    |
| StoryboardElementStateCondition  |   ✅    |   ✅    | Needs to manually specity storyboard element name |
| UserDefinedValueCondition        |   ✅    |   ✅    |
| TrafficSignalCondition           |   ✅    |   ✅    |
| TrafficSignalControllerCondition |   ✅    |   ✅    |
