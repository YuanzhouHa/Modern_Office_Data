import random
import re
import os
import unreal
from datetime import datetime
from typing import Optional, Callable

def clean_sequencer(level_sequence):
    bindings = level_sequence.get_bindings()
    for b in bindings:
        b.remove()

def select_random_asset(assets_path, asset_class=None, predicate:Optional[Callable]=None):
    print(f"Trying to list assets from: {assets_path}, filter class: {asset_class}")
    eal = unreal.EditorAssetLibrary()
    assets = eal.list_assets(assets_path)
    print(f"Found {len(assets)} assets in {assets_path}: {assets}")

    if asset_class is not None:
        filtered_assets = []
        for asset in assets:
            try:
                asset_name = os.path.splitext(asset)[0]
                asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_name)
                if asset_data.asset_class_path.asset_name == asset_class:
                    filtered_assets.append(asset)
            except Exception as e:
                print(f"Error while filtering asset: {asset} ({e})")
                continue

        assets = filtered_assets
        print(f"Filtered by class '{asset_class}', {len(assets)} assets left: {assets}")

    if predicate is not None:
        filtered_assets = []
        for asset in assets:
            try:
                if predicate(asset):
                    filtered_assets.append(asset)
            except Exception as e:
                print(f"Error in predicate for {asset} ({e})")
                continue

        assets = filtered_assets
        print(f"Filtered by predicate, {len(assets)} assets left: {assets}")

    if not assets:
        print(f"ERROR: No assets found in {assets_path} (asset_class={asset_class}) after filtering! Check if the path exists, assets are loaded, or class filter is too strict.")
        raise RuntimeError(f"No assets found in {assets_path} (asset_class={asset_class})")

    selected_asset_path = random.choice(assets)
    print(f"Selected asset: {selected_asset_path}")
    return selected_asset_path

def spawn_actor(asset_path, location=unreal.Vector(0.0, 0.0, 0.0)):
    obj = unreal.load_asset(asset_path)
    if not obj:
        print(f"ERROR: Failed to load asset at path: {asset_path}")
        raise RuntimeError(f"Failed to load asset: {asset_path}")
    rotation = unreal.Rotator(0, 0, 0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(object_to_use=obj,
                                                              location=location,
                                                              rotation=rotation)
    actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    return actor

def add_animation_to_actor(spawnable_actor, animation_path):
    anim_track = spawnable_actor.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    animation_section = anim_track.add_section()
    animation_asset = unreal.load_asset(animation_path)
    if not animation_asset:
        print(f"ERROR: Failed to load animation asset at path: {animation_path}")
        raise RuntimeError(f"Failed to load animation asset: {animation_path}")
    animation_section.params.animation = animation_asset
    frame_rate = 30
    start_frame = 0
    end_frame = animation_asset.get_editor_property('sequence_length') * frame_rate
    animation_section.set_range(start_frame, end_frame)

def find_relevant_assets(level_sequence):
    camera_re = re.compile("SuperCineCameraActor_([0-9]+)")
    target_point_re = re.compile("TargetPoint_([0-9]+)")

    cameras = {}
    target_points = {}
    skylight = None

    all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in all_actors:
        label = actor.get_actor_label()
        name = actor.get_name()
        camera_matches = camera_re.search(label)
        target_point_matches = target_point_re.search(label)

        if camera_matches is not None:
            cameras[camera_matches.group(1)] = actor
        if target_point_matches is not None:
            target_points[target_point_matches.group(1)] = actor
        if 'SkyLight' in name:
            skylight = actor

    print(f"find_relevant_assets: cameras found {list(cameras.keys())}, target_points found {list(target_points.keys())}, skylight found: {skylight is not None}")
    return cameras, target_points, skylight

def random_hdri(hdri_backdrop):
    selected_hdri_path = select_random_asset('/HDRIBackdrop/Textures')
    hdri_texture = unreal.load_asset(selected_hdri_path)
    if not hdri_texture:
        print(f"ERROR: Failed to load HDRI texture asset at path: {selected_hdri_path}")
        raise RuntimeError(f"Failed to load HDRI texture asset: {selected_hdri_path}")
    hdri_backdrop.set_editor_property('cubemap', hdri_texture)

def random_cubemap(skylight):
    cubemap_path = select_random_asset('/Game/HDRI/', asset_class='TextureCube')
    cubemap_asset = unreal.load_asset(cubemap_path)
    if not cubemap_asset:
        print(f"ERROR: Failed to load cubemap asset at path: {cubemap_path}")
        raise RuntimeError(f"Failed to load cubemap asset: {cubemap_path}")

    skylight_comp = skylight.get_editor_property('light_component')
    skylight_comp.set_editor_property('cubemap', cubemap_asset)
    skylight_comp.recapture_sky()

def bind_camera_to_level_sequence(level_sequence, camera, character_location, start_frame=0, num_frames=0, move_radius=500):
    camera_cuts_track = None
    for track in level_sequence.get_master_tracks():
        if track.get_class() == unreal.MovieSceneCameraCutTrack.static_class():
            camera_cuts_track = track
            break

    if camera_cuts_track is None:
        print("No Camera Cuts track found.")
        return

    sections = camera_cuts_track.get_sections()
    for section in sections:
        if isinstance(section, unreal.MovieSceneCameraCutSection):
            camera_binding = level_sequence.add_possessable(camera)
            camera_binding_id = level_sequence.get_binding_id(camera_binding)
            section.set_camera_binding_id(camera_binding_id)
            print("Camera cut updated to use:", camera.get_name())

    transform_track = camera_binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_range(start_frame, start_frame + num_frames)
    channels = transform_section.get_all_channels()
    loc_x_channel = channels[0]
    loc_y_channel = channels[1]
    loc_z_channel = channels[2]

    center_location = character_location + unreal.Vector(0.0, 0.0, 100.0)
    frames = [start_frame, start_frame + num_frames]
    for frame in frames:
        random_location = center_location + unreal.Vector(
            random.uniform(-move_radius, move_radius),
            random.uniform(-move_radius, move_radius),
            random.uniform(-move_radius/2, move_radius/2)
        )
        frame_number = unreal.FrameNumber(frame)
        loc_x_channel.add_key(frame_number, random_location.x)
        loc_y_channel.add_key(frame_number, random_location.y)
        loc_z_channel.add_key(frame_number, random_location.z)

def render(output_path, start_frame=0, num_frames=0, mode="rgb"):
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    pipelineQueue = subsystem.get_queue()
    for job in pipelineQueue.get_jobs():
        pipelineQueue.delete_job(job)

    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = ues.get_editor_world()
    map_name = current_world.get_path_name()

    job = pipelineQueue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.set_editor_property('map', unreal.SoftObjectPath(map_name))
    job.set_editor_property('sequence', unreal.SoftObjectPath('/Game/RenderSequencer'))

    job.author = "Voia"
    job.job_name = "Synthetic Data"

    if mode == 'rgb':
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/RGB")
    else:
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/CameraNormal")
    job.set_configuration(newConfig)

    outputSetting = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    outputSetting.output_resolution = unreal.IntPoint(1920, 1080)
    outputSetting.file_name_format = "Image.{render_pass}.{frame_number}"
    outputSetting.flush_disk_writes_per_shot = True
    outputSetting.output_directory = unreal.DirectoryPath(path=f'{output_path}/{mode}')
    use_custom_playback_range = num_frames > 0
    outputSetting.use_custom_playback_range = use_custom_playback_range
    outputSetting.custom_start_frame = start_frame
    outputSetting.custom_end_frame = start_frame + num_frames

    renderPass = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)

    jpg_settings = job.get_configuration().find_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
    job.get_configuration().remove_setting(jpg_settings)
    png_settings = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    png_settings.set_editor_property('write_alpha', False)

    job.get_configuration().initialize_transient_settings()

    error_callback = unreal.OnMoviePipelineExecutorErrored()
    def movie_error(pipeline_executor, pipeline_with_error, is_fatal, error_text):
        unreal.log(pipeline_executor)
        unreal.log(pipeline_with_error)
        unreal.log(is_fatal)
        unreal.log(error_text)
    error_callback.add_callable(movie_error)

    def movie_finished(pipeline_executor, success):
        unreal.log('movie finished')
        unreal.log(pipeline_executor)
        unreal.log(success)
        if mode == 'rgb':
            render(output_path=output_path, mode="normals")
    finished_callback = unreal.OnMoviePipelineExecutorFinished()
    finished_callback.add_callable(movie_finished)

    unreal.log("Starting Executor")
    global executor
    executor = unreal.MoviePipelinePIEExecutor(subsystem)
    executor.set_editor_property('on_executor_errored_delegate', error_callback)
    executor.set_editor_property('on_executor_finished_delegate', finished_callback)
    subsystem.render_queue_with_executor_instance(executor)

if __name__ == '__main__':
    level_sequence = unreal.EditorAssetLibrary.load_asset('/Game/RenderSequencer.RenderSequencer')
    clean_sequencer(level_sequence)

    cameras, target_points, skylight = find_relevant_assets(level_sequence)
    random_keys = [k for k in cameras.keys() if k in target_points.keys()]
    print(f"Intersection keys: {random_keys} (from cameras {list(cameras.keys())} and target_points {list(target_points.keys())})")
    if not random_keys:
        print("ERROR: No matching keys between cameras and target_points! 检查场景中是否有命名规则匹配的CineCamera和TargetPoint。")
        exit(1)
    random_key = random.choice(random_keys)
    camera = cameras[random_key]
    target_point = target_points[random_key]

    random_cubemap(skylight)
    location = target_point.get_actor_location()

    selected_skeletal_mesh_path = select_random_asset('/Game/ActorcoreCharacterBaked', asset_class='SkeletalMesh')
    a_pose_animation_name = os.path.splitext(selected_skeletal_mesh_path)[-1] + "_Anim"
    def not_a_pose_animation(asset:str):
        return not asset.endswith(a_pose_animation_name)
    baked_animation_directory_path = os.path.dirname(selected_skeletal_mesh_path)
    selected_animation_path = select_random_asset(baked_animation_directory_path, asset_class="AnimSequence", predicate=not_a_pose_animation)

    print(f"Skeletal Mesh: {selected_skeletal_mesh_path}")
    print(f"Animation: {selected_animation_path}")

    actor = spawn_actor(asset_path=selected_skeletal_mesh_path, location=location)
    spawnable_actor = level_sequence.add_spawnable_from_instance(actor)
    add_animation_to_actor(spawnable_actor, animation_path=selected_animation_path)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor)
    bind_camera_to_level_sequence(level_sequence, camera, location, start_frame=0, num_frames=300, move_radius=800)
    unreal.log(f"Selected character and animation: {selected_skeletal_mesh_path}, {selected_animation_path}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    render(output_path="D:\\SyntheticData\\MordenOffice\\RandomCamera\\" + timestamp + "\\", mode="rgb")
