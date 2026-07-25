Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$modelDir = Join-Path $repoRoot 'models\small_rover'
$modelPath = Join-Path $modelDir 'model.sdf'
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

function Write-MirroredObj {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath
    )

    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $output = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [System.IO.File]::ReadLines($SourcePath)) {
        if ($line.StartsWith('v ') -or $line.StartsWith('vn ')) {
            $parts = $line -split '\s+'
            $parts[1] = (-[double]::Parse($parts[1], $culture)).ToString('0.000000', $culture)
            $output.Add($parts -join ' ')
            continue
        }

        if ($line.StartsWith('f ')) {
            $parts = $line -split '\s+'
            [System.Array]::Reverse($parts, 1, $parts.Length - 1)
            $output.Add($parts -join ' ')
            continue
        }

        $output.Add($line)
    }

    [System.IO.File]::WriteAllLines(
        $DestinationPath,
        $output,
        [System.Text.UTF8Encoding]::new($false)
    )
}

$wheelMeshDir = Join-Path $repoRoot 'models\small_rover_wheels\meshes'
Write-MirroredObj `
    -SourcePath (Join-Path $wheelMeshDir 'Mecanum_Wheel_60mm_FrontRight.obj') `
    -DestinationPath (Join-Path $wheelMeshDir 'Mecanum_Wheel_60mm_FrontLeft.obj')
Write-MirroredObj `
    -SourcePath (Join-Path $wheelMeshDir 'Mecanum_Wheel_60mm_RearRight.obj') `
    -DestinationPath (Join-Path $wheelMeshDir 'Mecanum_Wheel_60mm_RearLeft.obj')

# CAD coordinates use +Y forward and +X right. Runtime frames use REP-103:
# +X forward, +Y left, +Z up. Wheel meshes retain their CAD local frame and
# are rotated -90 deg about Z at their link pose.
$wheelLocations = @(
    @{ Name = 'front_left';  Mesh = 'Mecanum_Wheel_60mm_FrontLeft.obj';  Front = $true;  MirrorX = $true;  MirrorY = $false; X = 0.064610;  Y = 0.090500 },
    @{ Name = 'front_right'; Mesh = 'Mecanum_Wheel_60mm_FrontRight.obj'; Front = $true;  MirrorX = $false; MirrorY = $false; X = 0.064610;  Y = -0.090500 },
    @{ Name = 'rear_left';   Mesh = 'Mecanum_Wheel_60mm_RearLeft.obj';   Front = $false; MirrorX = $true;  MirrorY = $false; X = -0.074500; Y = 0.090500 },
    @{ Name = 'rear_right';  Mesh = 'Mecanum_Wheel_60mm_RearRight.obj';  Front = $false; MirrorX = $false; MirrorY = $false; X = -0.074500; Y = -0.090500 }
)

# The corrected front-right reference has roller-axis plane angles of 5.38 deg
# to XZ, 45 deg to YZ, and 135.5 deg to XY. Each subsequent roller is the same
# transform rotated 45 degrees around the wheel axle.
$frontReferenceRollers = @(
    @{ Index = 0; X = 0.000003; Y = 0.022801000; Z = 0.003020000; Roll = 0.000000000; Pitch = 0.776639639; Yaw = 0.131828760 },
    @{ Index = 1; X = 0.000003; Y = 0.013987279; Z = 0.018258204; Roll = 0.888508739; Pitch = 0.443722978; Yaw = 0.671482516 },
    @{ Index = 2; X = 0.000003; Y = -0.003020000; Z = 0.022801000; Roll = 1.478126516; Pitch = -0.093895659; Yaw = 0.780996596 },
    @{ Index = 3; X = 0.000003; Y = -0.018258204; Z = 0.013987279; Roll = 2.130530953; Pitch = -0.596678917; Yaw = 0.545659158 },
    @{ Index = 4; X = 0.000003; Y = -0.022801000; Z = -0.003020000; Roll = 3.141592654; Pitch = -0.776639639; Yaw = -0.131828760 },
    @{ Index = 5; X = 0.000003; Y = -0.013987279; Z = -0.018258204; Roll = -2.253083915; Pitch = -0.443722978; Yaw = -0.671482516 },
    @{ Index = 6; X = 0.000003; Y = 0.003020000; Z = -0.022801000; Roll = -1.663466138; Pitch = 0.093895659; Yaw = -0.780996596 },
    @{ Index = 7; X = 0.000003; Y = 0.018258204; Z = -0.013987279; Roll = -1.011061701; Pitch = 0.596678917; Yaw = -0.545659158 }
)

# Rear-right is an independent measured assembly. The imported rear hub reverses
# the measured CAD Z sign, so its reference roller uses -45 deg local pitch.
# Rear-left mirrors the corrected assembly.
$rearReferenceRollers = @(
    @{ Index = 0; X = 0.000003; Y = 0.023000000; Z = 0.000031000; Roll = 0.000000000; Pitch = -0.785398163; Yaw = 0.000000000 },
    @{ Index = 1; X = 0.000003; Y = 0.016241536; Z = 0.016285376; Roll = 0.955316618; Pitch = -0.523598776; Yaw = -0.615479709 },
    @{ Index = 2; X = 0.000003; Y = -0.000031000; Z = 0.023000000; Roll = 1.570796327; Pitch = 0.000000000; Yaw = -0.785398163 },
    @{ Index = 3; X = 0.000003; Y = -0.016285376; Z = 0.016241536; Roll = 2.186276035; Pitch = 0.523598776; Yaw = -0.615479709 },
    @{ Index = 4; X = 0.000003; Y = -0.023000000; Z = -0.000031000; Roll = 3.141592654; Pitch = 0.785398163; Yaw = 0.000000000 },
    @{ Index = 5; X = 0.000003; Y = -0.016241536; Z = -0.016285376; Roll = -2.186276035; Pitch = 0.523598776; Yaw = 0.615479709 },
    @{ Index = 6; X = 0.000003; Y = 0.000031000; Z = -0.023000000; Roll = -1.570796327; Pitch = 0.000000000; Yaw = 0.785398163 },
    @{ Index = 7; X = 0.000003; Y = 0.016285376; Z = -0.016241536; Roll = -0.955316618; Pitch = -0.523598776; Yaw = 0.615479709 }
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
    $meshUri = "model://small_rover_wheels/meshes/$($wheel.Mesh)"
    $rollerUri = 'model://small_rover_wheels/meshes/roller_Varsayilan.obj'
    $x = $wheel.X.ToString('F6', [System.Globalization.CultureInfo]::InvariantCulture)
    $y = $wheel.Y.ToString('F6', [System.Globalization.CultureInfo]::InvariantCulture)
    $wheelPose = "$x $y 0.017000 0 0 -1.570796327"

    Add-Line "    <link name=`"${prefix}_wheel`">"
    Add-Line "      <pose relative_to=`"base_link`">$wheelPose</pose>"
    Add-Line '      <inertial><mass>0.030</mass><inertia><ixx>0.000008</ixx><iyy>0.000015</iyy><izz>0.000015</izz></inertia></inertial>'
    Add-Line "      <visual name=`"wheel_mesh`"><geometry><mesh><uri>$meshUri</uri></mesh></geometry></visual>"
    Add-Line '      <collision name="hub_collision"><pose>0 0 0 0 1.570796327 0</pose><geometry><cylinder><radius>0.017</radius><length>0.022</length></cylinder></geometry><surface><friction><ode><mu>0.8</mu><mu2>0.8</mu2></ode></friction></surface></collision>'
    Add-Line '    </link>'
    # All wheel joints use the same positive axle direction in the rover frame,
    # matching the stock Gazebo mecanum controller convention.
    Add-Line "    <joint name=`"${prefix}_wheel_joint`" type=`"revolute`"><pose relative_to=`"base_link`">$wheelPose</pose><parent>base_link</parent><child>${prefix}_wheel</child><axis><xyz expressed_in=`"base_link`">0 1 0</xyz><limit><lower>-1e16</lower><upper>1e16</upper><effort>1.5</effort><velocity>80</velocity></limit><dynamics><damping>0.0005</damping></dynamics></axis></joint>"

    $rollerSet = if ($wheel.Front) { $frontReferenceRollers } else { $rearReferenceRollers }
    foreach ($roller in $rollerSet) {
        $index = $roller.Index
        $rollerX = if ($wheel.MirrorX) { -$roller.X } else { $roller.X }
        $rollerY = if ($wheel.MirrorY) { -$roller.Y } else { $roller.Y }
        $rollerRoll = if ($wheel.MirrorY) { -$roller.Roll } else { $roller.Roll }
        $rollerPitch = if ($wheel.MirrorX) { -$roller.Pitch } else { $roller.Pitch }
        $rollerYaw = if ($wheel.MirrorX -xor $wheel.MirrorY) { -$roller.Yaw } else { $roller.Yaw }
        $poseValues = @($rollerX, $rollerY, $roller.Z, $rollerRoll, $rollerPitch, $rollerYaw | ForEach-Object {
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
