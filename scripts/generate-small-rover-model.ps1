Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$modelDir = Join-Path $repoRoot 'models\small_rover'
$modelPath = Join-Path $modelDir 'model.sdf'
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

# CAD coordinates use +Y forward and +X right.  Runtime frames use REP-103:
# +X forward, +Y left, +Z up.  Wheel meshes retain their CAD local frame and
# are rotated -90 deg about Z at their link pose. Mecanum handedness is paired
# diagonally: front-left with rear-right, front-right with rear-left.
$wheelLocations = @(
    @{ Name = 'front_left';  MeshModel = 'sverk_mecanum_wheel';       Mesh = 'Mecanum_Wheel_60mm_Left.obj';  RightHanded = $false; X = 0.064610;  Y = 0.090500 },
    @{ Name = 'front_right'; MeshModel = 'sverk_mecanum_wheel_right'; Mesh = 'Mecanum_Wheel_60mm_Right.obj'; RightHanded = $true;  X = 0.064610;  Y = -0.090500 },
    @{ Name = 'rear_left';   MeshModel = 'sverk_mecanum_wheel_right'; Mesh = 'Mecanum_Wheel_60mm_Right.obj'; RightHanded = $true;  X = -0.074500; Y = 0.090500 },
    @{ Name = 'rear_right';  MeshModel = 'sverk_mecanum_wheel';       Mesh = 'Mecanum_Wheel_60mm_Left.obj';  RightHanded = $false; X = -0.074500; Y = -0.090500 }
)

# Positions and RPY values are measured in each wheel's CAD frame.  The local
# X axis of every roller is its axle and is made the passive joint axis.
$rollers = @(
    @{ Index = 0; X = 0.000003; Y = 0.022937000; Z = -0.001705000; Roll = 0.000000000; Pitch = 0.782577251; Yaw = -0.075350181 },
    @{ Index = 1; X = 0.000003; Y = 0.017424525; Z = 0.015013291; Roll = 0.988897628; Pitch = 0.566086368; Yaw = 0.577602867 },
    @{ Index = 2; X = 0.000003; Y = 0.001705000; Z = 0.022937000; Roll = 1.623977028; Pitch = 0.053405549; Yaw = 0.783997995 },
    @{ Index = 3; X = 0.000003; Y = -0.015013291; Z = 0.017424525; Roll = 2.223416667; Pitch = -0.478943805; Yaw = 0.648925998 },
    @{ Index = 4; X = 0.000003; Y = -0.022937000; Z = 0.001705000; Roll = 3.141592654; Pitch = -0.782577251; Yaw = 0.075350181 },
    @{ Index = 5; X = 0.000003; Y = -0.017424525; Z = -0.015013291; Roll = -2.152695026; Pitch = -0.566086368; Yaw = -0.577602867 },
    @{ Index = 6; X = 0.000003; Y = -0.001705000; Z = -0.022937000; Roll = -1.517615626; Pitch = -0.053405549; Yaw = -0.783997995 },
    @{ Index = 7; X = 0.000003; Y = 0.015013291; Z = -0.017424525; Roll = -0.918175987; Pitch = 0.478943805; Yaw = -0.648925998 }
)

$lines = [System.Collections.Generic.List[string]]::new()
function Add-Line([string]$line) { $lines.Add($line) }

Add-Line '<?xml version="1.0"?>'
Add-Line '<sdf version="1.10">'
Add-Line '  <model name="small_rover">'
Add-Line '    <self_collide>false</self_collide>'
Add-Line '    <link name="base_link">'
Add-Line '      <inertial><mass>0.764</mass><inertia><ixx>0.0038</ixx><iyy>0.0041</iyy><izz>0.0060</izz></inertia></inertial>'
Add-Line '      <visual name="base_mesh"><pose>0 0 0 0 0 -1.570796327</pose><geometry><mesh><uri>model://small_rover_base/meshes/Rover_base_clean.obj</uri></mesh></geometry></visual>'
Add-Line '      <collision name="chassis_collision"><pose>0.010 0 0.040 0 0 0</pose><geometry><box><size>0.200 0.180 0.070</size></box></geometry><surface><friction><ode><mu>0.8</mu><mu2>0.8</mu2></ode></friction></surface></collision>'
Add-Line '    </link>'
Add-Line ''
Add-Line '    <link name="lidar_link">'
Add-Line '      <pose relative_to="base_link">0.065517 0 0.081 0 0 0</pose>'
Add-Line '      <inertial><mass>0.020</mass><inertia><ixx>0.00001</ixx><iyy>0.00001</iyy><izz>0.00001</izz></inertia></inertial>'
Add-Line '      <visual name="lidar_mesh"><pose>0 0 0 0 0 -1.570796327</pose><geometry><mesh><uri>model://RPLIDAR_C1_v1/meshes/RPLIDAR C1 v1.obj</uri></mesh></geometry><material><ambient>0.792157 0.819608 0.933333 1</ambient><diffuse>0.792157 0.819608 0.933333 1</diffuse><specular>0.2 0.2 0.2 1</specular></material></visual>'
Add-Line '      <collision name="lidar_collision"><pose>0 0 0.020 0 0 0</pose><geometry><cylinder><radius>0.032</radius><length>0.041</length></cylinder></geometry></collision>'
Add-Line '      <sensor name="rover_lidar" type="gpu_lidar"><pose>0 0 0.03 0 0 0</pose><topic>/small_rover/lidar/scan</topic><update_rate>10</update_rate><ray><scan><horizontal><samples>360</samples><resolution>1</resolution><min_angle>-3.141592654</min_angle><max_angle>3.141592654</max_angle></horizontal><vertical><samples>1</samples><resolution>1</resolution><min_angle>0</min_angle><max_angle>0</max_angle></vertical></scan><range><min>0.02</min><max>12.0</max><resolution>0.001</resolution></range></ray><always_on>true</always_on><visualize>true</visualize></sensor>'
Add-Line '    </link>'
Add-Line '    <joint name="lidar_joint" type="fixed"><parent>base_link</parent><child>lidar_link</child></joint>'
Add-Line ''

foreach ($wheel in $wheelLocations) {
    $prefix = $wheel.Name
    $meshUri = "model://$($wheel.MeshModel)/meshes/$($wheel.Mesh)"
    $rollerUri = "model://$($wheel.MeshModel)/meshes/roller_Varsayilan.obj"
    $x = $wheel.X.ToString('F6', [System.Globalization.CultureInfo]::InvariantCulture)
    $y = $wheel.Y.ToString('F6', [System.Globalization.CultureInfo]::InvariantCulture)
    $wheelPose = "$x $y 0.017000 0 0 -1.570796327"

    Add-Line "    <link name=`"${prefix}_wheel`">"
    Add-Line "      <pose relative_to=`"base_link`">$wheelPose</pose>"
    Add-Line '      <inertial><mass>0.030</mass><inertia><ixx>0.000008</ixx><iyy>0.000015</iyy><izz>0.000015</izz></inertia></inertial>'
    Add-Line "      <visual name=`"wheel_mesh`"><geometry><mesh><uri>$meshUri</uri></mesh></geometry></visual>"
    Add-Line '      <collision name="hub_collision"><pose>0 0 0 0 1.570796327 0</pose><geometry><cylinder><radius>0.017</radius><length>0.022</length></cylinder></geometry><surface><friction><ode><mu>0.8</mu><mu2>0.8</mu2></ode></friction></surface></collision>'
    Add-Line '    </link>'
    # The wheel mesh, cylinder collision, and roller layout all use local X as
    # their axle. The joint pose maps that local axle into the rover's lateral
    # direction, so the controller must drive local X as well.
    Add-Line "    <joint name=`"${prefix}_wheel_joint`" type=`"revolute`"><pose relative_to=`"base_link`">$wheelPose</pose><parent>base_link</parent><child>${prefix}_wheel</child><axis><xyz>1 0 0</xyz><limit><lower>-1e16</lower><upper>1e16</upper><effort>1.5</effort><velocity>80</velocity></limit><dynamics><damping>0.0005</damping></dynamics></axis></joint>"

    $isRightWheel = $wheel.RightHanded
    foreach ($roller in $rollers) {
        $index = $roller.Index
        $rollerY = if ($isRightWheel) { -$roller.Y } else { $roller.Y }
        $rollerRoll = if ($isRightWheel) { -$roller.Roll } else { $roller.Roll }
        $rollerYaw = if ($isRightWheel) { -$roller.Yaw } else { $roller.Yaw }
        $poseValues = @($roller.X, $rollerY, $roller.Z, $rollerRoll, $roller.Pitch, $rollerYaw | ForEach-Object {
            $_.ToString('0.000000000', [System.Globalization.CultureInfo]::InvariantCulture)
        })
        $pose = $poseValues -join ' '
        Add-Line "    <link name=`"${prefix}_roller_${index}`"><pose relative_to=`"${prefix}_wheel`">$pose</pose><inertial><mass>0.003</mass><inertia><ixx>0.00000002</ixx><iyy>0.00000024</iyy><izz>0.00000024</izz></inertia></inertial><visual name=`"mesh`"><geometry><mesh><uri>$rollerUri</uri></mesh></geometry></visual><collision name=`"roller_contact`"><pose>0 0 0 0 1.570796327 0</pose><geometry><cylinder><radius>0.0059</radius><length>0.0308</length></cylinder></geometry><surface><friction><ode><mu>1.2</mu><mu2>0.9</mu2></ode></friction></surface></collision></link>"
        Add-Line "    <joint name=`"${prefix}_roller_${index}_joint`" type=`"revolute`"><pose relative_to=`"${prefix}_wheel`">$pose</pose><parent>${prefix}_wheel</parent><child>${prefix}_roller_${index}</child><axis><xyz>1 0 0</xyz><limit><lower>-1e16</lower><upper>1e16</upper><effort>0</effort><velocity>1000</velocity></limit><dynamics><damping>0.00001</damping><friction>0.00001</friction></dynamics></axis></joint>"
    }
    Add-Line ''
}

Add-Line '    <plugin filename="gz-sim-mecanum-drive-system" name="gz::sim::systems::MecanumDrive">'
Add-Line '      <front_left_joint>front_left_wheel_joint</front_left_joint>'
Add-Line '      <front_right_joint>front_right_wheel_joint</front_right_joint>'
Add-Line '      <back_left_joint>rear_left_wheel_joint</back_left_joint>'
Add-Line '      <back_right_joint>rear_right_wheel_joint</back_right_joint>'
Add-Line '      <wheel_separation>0.181</wheel_separation>'
Add-Line '      <wheelbase>0.13911</wheelbase>'
Add-Line '      <wheel_radius>0.030</wheel_radius>'
Add-Line '      <topic>/small_rover/gz_cmd_vel</topic>'
Add-Line '      <odom_topic>/small_rover/odometry</odom_topic>'
Add-Line '      <frame_id>odom</frame_id>'
Add-Line '      <child_frame_id>base_link</child_frame_id>'
Add-Line '      <odom_publish_frequency>50</odom_publish_frequency>'
Add-Line '      <min_acceleration>-2.0</min_acceleration>'
Add-Line '      <max_acceleration>2.0</max_acceleration>'
Add-Line '      <max_velocity>0.6</max_velocity>'
Add-Line '    </plugin>'
Add-Line '    <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher"><topic>/small_rover/joint_state</topic></plugin>'
Add-Line '  </model>'
Add-Line '</sdf>'

[System.IO.File]::WriteAllLines($modelPath, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Host "Generated $modelPath"
