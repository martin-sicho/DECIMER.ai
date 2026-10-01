<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Maximum structures per OCSR request
    |--------------------------------------------------------------------------
    |
    | The number of segmented chemical structures that a single /decimer-ocsr
    | request will run OCSR on. Set to 0 (or any non-positive value) to process
    | all detected structures without a limit.
    |
    */

    'max_structures' => (int) env('OCSR_MAX_STRUCTURES', 0),

];
